"""The reading library has to survive a disk that does not.

Two constraints meet here and neither bends. The corpus is **owner-only** --
ERR transcripts are © ERR, Selges keeles carries no reuse grant -- so it cannot
ship inside an image built from a public repository. And Cloud Run's disk is
**ephemeral**, so a file copied into a container is gone at the next cold start.

So a harvest is pushed to the origin, the Worker archives it, and every
container that starts afterwards is handed it back. These tests cover the two
ends the app owns: receiving a push, and handing the archive back.

The push is authenticated by `STATE_TOKEN`, not by Cloudflare Access. That is
not a shortcut -- Access is an interactive login, and a script cannot satisfy
one. The Worker is guarded by Access; the origin is guarded by tokens; the
upload is a machine, so it goes to the origin.
"""

from __future__ import annotations

import base64

import pytest

pytest.importorskip("httpx", reason="TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402
from eesti import config  # noqa: E402

TOKEN = "state-token-for-tests"


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONTENT_DB", str(tmp_path / "content.db"))
    monkeypatch.setenv("STATE_TOKEN", TOKEN)
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


@pytest.fixture
def harvest(tmp_path):
    """A real content database with one item in it, base64'd for the wire."""
    from eesti.sources import Item, add_items, connect, register

    path = tmp_path / "harvest.db"
    conn = connect(path)
    register(conn)
    source = conn.execute("SELECT id FROM sources LIMIT 1").fetchone()["id"]
    add_items(conn, [Item(
        source_id=source, skill="lugemine", level="B1",
        title="Proovitekst", body="Ma lugesin raamatu läbi.",
    )])
    conn.close()
    return base64.b64encode(path.read_bytes()).decode("ascii")


class TestReceivingAHarvest:
    def test_a_pushed_library_becomes_readable(self, deployment, harvest):
        pushed = deployment.post(
            "/api/content/import",
            json={"database": harvest},
            headers={"x-state-token": TOKEN},
        )
        assert pushed.status_code == 200, pushed.text
        assert pushed.json()["items"] == 1

        listed = deployment.get("/api/library")
        assert [i["title"] for i in listed.json()["items"]] == ["Proovitekst"]

    def test_health_flips_once_there_is_something_to_read(
        self, deployment, harvest
    ):
        assert deployment.get("/api/health").json()["library"] is False
        deployment.post("/api/content/import", json={"database": harvest},
                        headers={"x-state-token": TOKEN})
        assert deployment.get("/api/health").json()["library"] is True

    def test_a_second_push_replaces_the_first(self, deployment, harvest):
        """Unlike the learner snapshot, this one overwrites on purpose: a corpus
        is derived from a harvest, so there is no accumulated work to lose, and
        refusing would make re-harvesting impossible."""
        for _ in range(2):
            response = deployment.post(
                "/api/content/import", json={"database": harvest},
                headers={"x-state-token": TOKEN},
            )
            assert response.status_code == 200
        assert deployment.get("/api/library").json()["items"] != []

    def test_no_token_no_push(self, deployment, harvest):
        response = deployment.post("/api/content/import",
                                   json={"database": harvest})
        assert response.status_code == 403

    def test_a_wrong_token_no_push(self, deployment, harvest):
        response = deployment.post("/api/content/import",
                                   json={"database": harvest},
                                   headers={"x-state-token": "guess"})
        assert response.status_code == 403


class TestHandingItBack:
    def test_an_empty_deployment_reports_nothing_to_archive(self, deployment):
        body = deployment.get("/api/content/export",
                              headers={"x-state-token": TOKEN}).json()
        assert body["present"] is False
        assert "database" not in body

    def test_the_cheap_answer_does_not_carry_the_database(
        self, deployment, harvest
    ):
        """The Worker asks this on every cold start; the answer is megabytes,
        so it has to be opt-in."""
        deployment.post("/api/content/import", json={"database": harvest},
                        headers={"x-state-token": TOKEN})
        body = deployment.get("/api/content/export",
                              headers={"x-state-token": TOKEN}).json()
        assert body["present"] is True
        assert "database" not in body

    def test_the_full_answer_round_trips(self, deployment, harvest):
        """What comes out must be pushable straight back in -- that is the whole
        archive-and-restore path, and it is the same key on both sides."""
        deployment.post("/api/content/import", json={"database": harvest},
                        headers={"x-state-token": TOKEN})
        exported = deployment.get("/api/content/export?full=1",
                                  headers={"x-state-token": TOKEN}).json()

        restored = deployment.post(
            "/api/content/import",
            json={"database": exported["database"]},
            headers={"x-state-token": TOKEN},
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["items"] == 1

    def test_export_needs_the_token_too(self, deployment):
        assert deployment.get("/api/content/export").status_code == 403
