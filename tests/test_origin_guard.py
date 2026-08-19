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
