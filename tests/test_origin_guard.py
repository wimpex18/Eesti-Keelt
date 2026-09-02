"""The origin must not be a way around the front door.

The app runs on Cloud Run with unauthenticated invocations allowed, because
that is what the free tier requires. Cloudflare Access sits in front of the
*Worker*, not in front of the `run.app` URL, so on its own Access would guard
one of two doors and the owner-only harvested material would be a hostname
guess away.

`PROXY_TOKEN` is the second door's lock: a secret only the Worker holds. These
tests pin the two halves of that — the lock works when a key is configured, and
it stays out of the way when none is, because the default way to run this app
is `cli serve` on a laptop.

They also pin the boot id, which is not decoration: it is the only signal the
Worker gets that Cloud Run replaced the instance and its learner databases are
gone. If it stops changing across processes, or stops appearing on responses,
snapshots stop being restored and the failure is silent.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx", reason="TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app_module.app)


class TestOriginGuard:
    def test_open_when_no_token_is_configured(self, client, monkeypatch):
        monkeypatch.delenv("PROXY_TOKEN", raising=False)
        assert client.get("/api/health").status_code == 200

    def test_refuses_a_request_without_the_token(self, client, monkeypatch):
        monkeypatch.setenv("PROXY_TOKEN", "s3cret")
        assert client.get("/api/health").status_code == 403

    def test_refuses_the_wrong_token(self, client, monkeypatch):
        monkeypatch.setenv("PROXY_TOKEN", "s3cret")
        response = client.get("/api/health", headers={"x-proxy-token": "guess"})
        assert response.status_code == 403

    def test_accepts_the_right_token(self, client, monkeypatch):
        monkeypatch.setenv("PROXY_TOKEN", "s3cret")
        response = client.get("/api/health", headers={"x-proxy-token": "s3cret"})
        assert response.status_code == 200

    def test_the_guard_covers_the_page_too_not_just_the_api(
        self, client, monkeypatch
    ):
        """A reader who can fetch `/` can read the library through it."""
        monkeypatch.setenv("PROXY_TOKEN", "s3cret")
        assert client.get("/").status_code == 403

    def test_health_reports_whether_the_guard_is_on(self, client, monkeypatch):
        """So "is the deployment closed?" is checkable, not assumed."""
        monkeypatch.delenv("PROXY_TOKEN", raising=False)
        assert client.get("/api/health").json()["origin_guarded"] is False

        monkeypatch.setenv("PROXY_TOKEN", "s3cret")
        guarded = client.get("/api/health", headers={"x-proxy-token": "s3cret"})
        assert guarded.json()["origin_guarded"] is True


class TestBootId:
    def test_every_response_carries_it(self, client):
        assert client.get("/api/health").headers.get("x-boot-id")

    def test_it_is_stable_within_a_process(self, client):
        first = client.get("/api/health").headers["x-boot-id"]
        second = client.get("/api/health").headers["x-boot-id"]
        assert first == second

    def test_health_and_header_agree(self, client):
        response = client.get("/api/health")
        assert response.json()["boot"] == response.headers["x-boot-id"]

    def test_it_is_not_a_constant(self):
        """A hard-coded value would mean the Worker never restores anything."""
        assert app_module.BOOT_ID != "" and len(app_module.BOOT_ID) >= 8


class TestTheWorkerRefusesTheBackChannel:
    """The second lock on the endpoints that overwrite the learner.

    `_require_state_token` says in its own docstring that a restore endpoint
    "does not rely on a single layer" — Access guards the Worker, the token
    guards the route. The Worker's half of that was
    `startsWith("/api/state/")`, which is a naming convention rather than the
    set it meant. Five origin routes require `STATE_TOKEN` and that prefix
    covered two: `/api/progress/reset`, which erases the learner's practice
    history, and `/api/content/import`, which overwrites the corpus, were
    proxied straight through.

    Never an open door — the origin demands the token either way, and a request
    without it gets 403. What was missing is the layer the design says it has.

    A Worker cannot import Python, so the list is hand-maintained and therefore
    checked in both directions, the way `api.ROUTERS`, `cli.GROUPS` and
    `eval.yml`'s provider list are. Deriving the origin half rather than
    restating it is the point: a route that starts requiring the token is
    covered here without anybody remembering to come back.
    """

    @staticmethod
    def _token_guarded() -> set[str]:
        """Every origin route that calls `_require_state_token`, from source."""
        import re

        from pathlib import Path

        src = (Path(__file__).resolve().parents[1] / "eesti" / "api" / "state.py"
               ).read_text(encoding="utf-8")
        return {
            m.group(2)
            for m in re.finditer(
                r'@router\.(get|post)\("([^"]+)"\)(.*?)(?=@router\.|\Z)', src, re.S)
            if "_require_state_token" in m.group(3)
        }

    @staticmethod
    def _worker_blocks() -> set[str]:
        import re

        from pathlib import Path

        src = (Path(__file__).resolve().parents[1] / "deploy" / "worker.ts"
               ).read_text(encoding="utf-8")
        block = re.search(r"const BACK_CHANNEL = \[(.*?)\];", src, re.S)
        assert block, "the Worker's block list changed shape"
        return set(re.findall(r'"([^"]+)"', block.group(1)))

    def test_the_origin_really_does_guard_five_routes(self):
        """The guard on the guard: if this finds nothing, both assertions below
        pass vacuously."""
        assert len(self._token_guarded()) >= 5

    def test_every_token_guarded_route_is_refused_by_the_worker(self):
        exposed = sorted(self._token_guarded() - self._worker_blocks())
        assert not exposed, (
            f"{exposed} require STATE_TOKEN on the origin and are proxied "
            f"through the Worker, so they rest on one layer instead of two")

    def test_the_worker_blocks_nothing_that_is_not_guarded(self):
        """The other direction. A path 404'd here that the origin serves
        normally would be a feature quietly removed from the deployment while
        it kept working under `cli serve`."""
        phantom = sorted(self._worker_blocks() - self._token_guarded())
        assert not phantom, (
            f"the Worker refuses {phantom}, which no origin route guards — "
            f"either it is dead weight or it broke a working endpoint")

    def test_it_matches_on_the_whole_path_not_a_prefix(self):
        """The original bug. A prefix is a naming convention; the thing being
        guarded is a set of routes, and the two drifted the moment a guarded
        route was named something else.

        Comments stripped first: the comment above the fix *quotes* the old
        `startsWith` so the next reader knows what changed, and a naive search
        finds it there. Three assertions in this repository have now been
        written that way and passed on their own prose.
        """
        import re

        from pathlib import Path

        src = (Path(__file__).resolve().parents[1] / "deploy" / "worker.ts"
               ).read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        code = "\n".join(line for line in code.splitlines()
                          if not line.lstrip().startswith("//"))
        assert 'startsWith("/api/state/")' not in code
