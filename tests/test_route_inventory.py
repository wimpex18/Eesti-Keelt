"""Every route must have a caller, or a written reason for not having one.

This file exists because of a count. Six times in this project the page and
the server drifted apart and nothing failed:

  * the reading list sent `level=` after the column became `band` — empty list
  * the fetch helper was POST-only, so every GET route would have 405'd
  * `/api/library/{id}` read without recording, so reading counted for nothing
  * four endpoints were built and never wired to anything
  * `TABS` lost three panels, so two could not be opened and one never hid
  * two library sections — 82 items — could not be reached from the page

`test_ui_contract.py` covers one direction: everything the page calls must
exist. That finds typos. It cannot find something nobody wired up, and five of
those six were exactly that.

Measured when this was written: **10 of 47 API routes had no caller anywhere** —
21 % of the surface. The worst was `POST /api/vocab/known`, the only way a word
can be marked known. Its other caller is `cli vocab`, which does not exist on
the deployment, so on the running app no word could ever become known — and the
comprehensible-input ordering, dictation's easiest-first ordering, the
vocabulary line in the verdict and the "N of the first 4000" counter all sat at
zero permanently. Nothing errored.

The idea is borrowed from API-coverage reporting (Specmatic and similar), which
compares the implemented surface against the consumed one and flags both
directions. Doing it at source level rather than from traffic suits this
project: one page, one server, no build step, and a test that runs offline.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: Where a route may legitimately be called from.
CONSUMERS = {
    "page": ("eesti/web/index.html",),
    "cli": ("eesti/cli.py",),
    "worker": ("deploy/worker.ts",),
    "scripts": ("deploy/*.sh",),
    "ci": (".github/workflows/*.yml",),
}

#: Routes with no caller, and why that is the right answer for each.
#:
#: An entry here is a decision, not a snooze. The reason has to say who the
#: route is for, because "nobody calls it" and "the Worker will call it once
#: X ships" are different states and only one of them is fine.
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
    """Every `/api/` path the app serves.

    From `eesti.api.paths()`, not from `app.routes`. FastAPI keeps an included
    router as one lazy `_IncludedRouter` entry, so the obvious walk --
    `{r.path for r in app.routes if hasattr(r, "path")}` -- returns four paths
    and raises nothing. This check would then have passed by measuring almost
    nothing, which is the exact failure it exists to catch in the app.
    """
    from eesti import api
    from eesti.app import app

    return sorted(p for p in api.paths(app) if p.startswith("/api/"))


def test_the_inventory_is_not_empty(routes):
    """The guard on the guard: every assertion below is over `routes`, so a
    change that makes it short makes them all pass."""
    assert len(routes) > 40, f"only {len(routes)} routes found -- the walk broke"


def callers(path: str, sources: dict[str, str]) -> list[str]:
    """Which consumers mention this route.

    A parameterised route is called by its prefix — `"/api/library/" + id` —
    so the stem is what is searched for.
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
    """An exemption for a route that no longer exists is a stale note that
    would silently excuse a future route of the same name."""
    stale = [p for p in EXEMPT if p not in routes]
    assert not stale, f"EXEMPT names routes that do not exist: {stale}"


def test_every_exemption_gives_a_reason(routes):
    for path, reason in EXEMPT.items():
        assert len(reason) > 40, f"{path} is exempt without saying why"


def test_the_word_marking_route_is_reachable_from_the_page(sources):
    """Singled out because it was the costly one. `set_status` is the only way
    a lemma becomes known, and its two callers were this route — uncalled —
    and a CLI that does not exist on the deployment. Everything that orders
    material by what the learner already knows depended on it."""
    assert "/api/vocab/known" in sources["page"]


def test_the_only_other_writer_is_the_cli(sources):
    """If a second writer appears, this test should be updated deliberately —
    an inferred "known" would measure reading rather than vocabulary."""
    import subprocess

    got = subprocess.run(
        ["grep", "-rln", "--include=*.py", "set_status", "eesti/"],
        capture_output=True, text=True, cwd=ROOT).stdout.split()
    assert sorted(got) == ["eesti/api/vocab.py", "eesti/cli.py", "eesti/vocab.py"]
