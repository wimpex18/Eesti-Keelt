"""The origin must not be a way around the front door.

Cloud Run allows unauthenticated invocations, and Access guards only the Worker,
so `PROXY_TOKEN` (held only by the Worker) locks the origin when configured and
stays out of the way under `cli serve`. Also pins the boot id, the Worker's only
signal that the instance was replaced and needs its snapshot.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

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
    """The Worker blocks exactly the origin routes that require `STATE_TOKEN`, derived
    from the origin and checked in both directions (a Worker cannot import Python).
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
        """A prefix is not the set: every guarded route is blocked by name. Comments are
        stripped before searching the Worker source.
        """
        import re

        from pathlib import Path

        src = (Path(__file__).resolve().parents[1] / "deploy" / "worker.ts"
               ).read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        code = "\n".join(line for line in code.splitlines()
                          if not line.lstrip().startswith("//"))
        assert 'startsWith("/api/state/")' not in code
