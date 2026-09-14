"""Every route must have a caller, or a written reason for not having one.

`test_ui_contract.py` checks that everything the page calls exists; this checks
the other direction — every `/api/*` route is referenced by the page, the Worker
or a deploy script. A route nobody calls is a feature that silently does not
work on the deployment.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: Where a route may legitimately be called from.
CONSUMERS = {
    "page": ("eesti/web/index.html", "eesti/web/js/*.js"),
    "cli": ("eesti/cli/*.py",),
    "worker": ("deploy/worker.ts",),
    "scripts": ("deploy/*.sh",),
    "ci": (".github/workflows/*.yml",),
}

#: Routes with no caller, and why that is right for each. The reason must say who
#: the route is for.
EXEMPT: dict[str, str] = {
    "/api/docs": (
        "FastAPI's own interactive documentation. Its caller is a human with a "
        "browser, which is the point of it."
    ),
}


def _text(patterns: tuple[str, ...]) -> str:
    out = []
    for pattern in patterns:
        if "*" in pattern:
            out += [p.read_text(encoding="utf-8") for p in sorted(ROOT.glob(pattern))]
        else:
            path = ROOT / pattern
            if path.exists():
                out.append(path.read_text(encoding="utf-8"))
    return "\n".join(out)


@pytest.fixture(scope="module")
def sources() -> dict[str, str]:
    return {name: _text(globs) for name, globs in CONSUMERS.items()}


@pytest.fixture(scope="module")
def routes() -> list[str]:
    """Every `/api/` path the app serves, from `eesti.api.paths()` (walking
    `app.routes` misses included routers).
    """
    from eesti import api
    from eesti.app import app

    return sorted(p for p in api.paths(app) if p.startswith("/api/"))


def test_the_inventory_is_not_empty(routes):
    """The guard on the guard: every assertion below is over `routes`, so a
    change that makes it short makes them all pass."""
    assert len(routes) > 40, f"only {len(routes)} routes found -- the walk broke"


def callers(path: str, sources: dict[str, str]) -> list[str]:
    """Which consumers mention this route; a parameterised route is found by its
    prefix.
    """
    stem = re.sub(r"\{[^}]+\}.*$", "", path).rstrip("/")
    return [name for name, text in sources.items() if stem and stem in text]


def test_every_route_has_a_caller_or_a_reason(routes, sources):
    orphans = [p for p in routes if not callers(p, sources) and p not in EXEMPT]
    assert not orphans, (
        "these routes cannot be reached by anything:\n  "
        + "\n  ".join(orphans)
        + "\n\nWire one up, or add it to EXEMPT with a reason saying who it is "
          "for. An endpoint nobody can call is the same bug as a measurement "
          "nobody writes."
    )


def test_the_exemptions_are_still_routes(routes):
    """An exemption for a route that no longer exists must be removed."""
    stale = [p for p in EXEMPT if p not in routes]
    assert not stale, f"EXEMPT names routes that do not exist: {stale}"


def test_every_exemption_gives_a_reason(routes):
    for path, reason in EXEMPT.items():
        assert len(reason) > 40, f"{path} is exempt without saying why"


def test_the_word_marking_route_is_reachable_from_the_page(sources):
    """`POST /api/vocab/known` — the only way a word becomes known on the deployment —
    has a caller in the page.
    """
    assert "/api/vocab/known" in sources["page"]


def test_the_only_other_writer_is_the_cli():
    """`vocab.set_status` has only the expected writers, found by parsing (`ast`), not
    by grepping prose.
    """
    import ast

    writers = []
    for path in sorted((ROOT / "eesti").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            named = (
                # A call, or an import of it by name.
                (isinstance(node, ast.Name) and node.id == "set_status")
                or (isinstance(node, ast.Attribute) and node.attr == "set_status")
                # And where it lives: `vocab.py` belongs in this list because
                # it defines the ladder, not because it writes to it.
                or (isinstance(node, ast.FunctionDef) and node.name == "set_status")
            )
            if named:
                writers.append(str(path.relative_to(ROOT)))
                break
    assert sorted(writers) == ["eesti/api/vocab.py", "eesti/cli/report.py",
                               "eesti/vocab.py"]


class TestEveryRouterIsRegistered:
    """`api.ROUTERS` is hand-ordered (registration order matters), so it is checked
    against the modules in both directions.
    """

    @staticmethod
    def _modules() -> dict[str, object]:
        import importlib
        import pkgutil

        from eesti import api

        out = {}
        for info in pkgutil.iter_modules(api.__path__):
            module = importlib.import_module(f"eesti.api.{info.name}")
            if hasattr(module, "router"):
                out[info.name] = module
        return out

    def test_there_are_routers_to_check(self):
        assert len(self._modules()) >= 8

    def test_every_router_in_the_package_is_registered(self):
        from eesti import api

        missing = sorted(name for name, module in self._modules().items()
                         if module.router not in api.ROUTERS)
        assert not missing, (
            f"{missing} declare routes that nothing serves: add them to "
            f"api.ROUTERS, in the position their paths need")

    def test_no_router_is_registered_twice(self):
        from eesti import api

        assert len(api.ROUTERS) == len(set(map(id, api.ROUTERS)))

    def test_every_registered_router_comes_from_the_package(self):
        from eesti import api

        known = {id(m.router) for m in self._modules().values()}
        assert all(id(r) in known for r in api.ROUTERS)


class TestTheOrderThatIsBehaviour:
    """`/api/library` and `/api/library/{item_id}` are the pair that made the
    registration order load-bearing. The comment in `api/__init__.py` says so;
    this asks the app."""

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        from eesti import app as app_module
        from eesti import config

        for name, stem in (("PROGRESS_DB", "p"), ("REVIEW_DB", "r"),
                           ("VOCAB_DB", "v"), ("NOTION_DB", "n")):
            monkeypatch.setattr(config, name, str(tmp_path / f"{stem}.db"))
        return TestClient(app_module.app)

    def test_the_collection_route_is_not_swallowed_by_the_item_route(self, client):
        """`/api/library` is registered before `/api/library/{item_id}`."""
        got = client.get("/api/library?skill=lugemine&limit=5")
        assert got.status_code == 200
        assert "items" in got.json()

    def test_the_item_route_still_answers(self, client):
        got = client.get("/api/library/does-not-exist")
        assert got.status_code == 404, got.text
