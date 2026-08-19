"""Reading has to leave a trace, or half the app measures nothing.

`library.open_item` writes two things when a text is opened: an exposure row,
and a vocabulary encounter for every content lemma. `/api/library/{item_id}` --
the only way the web app ever opens a text -- did a raw SELECT instead and
wrote neither.

Everything downstream quietly reported nothing:

- readiness said "0 текстов" for Lugemine however much was read
- `parts_touched` saw no contact, so every exam part stayed untouched forever
- `vocab_status` stayed empty, so the reading recommendation could never rank
  by what the learner knows

This is the third time this project has built a measurement without its writer
-- the vocabulary table, the snapshot restore, and now this -- so the tests are
about the *writing*, which is the half that keeps going missing.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx", reason="TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402
from eesti.library import exposure, parts_touched  # noqa: E402
from eesti.progress import connect as progress_connect  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client with its own corpus as well as its own learner state.

    Seeded rather than borrowed: an earlier version read whatever corpus the
    developer happened to have, which meant these tests skipped in CI and
    proved nothing about the writer they exist to protect.
    """
    from eesti import config
    from eesti.sources import Item, add_items, connect as content_connect
    from eesti.sources import register

    content_path = tmp_path / "content.db"
    conn = content_connect(content_path)
    register(conn)
    add_items(conn, [
        Item("selges-keeles", "lugemine", band="kergem", title="Lihtne lugu",
             body="Ma lugesin raamatu läbi ja läksin koju. "
                  "Poiss ostis auto ära ning sõitis linna."),
        Item("err-r4", "kuulamine", title="Saade", body="",
             audio_url="https://x/a.mp3"),
    ])
    conn.close()

    monkeypatch.setattr(config, "CONTENT_DB", str(content_path))
    monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(app_module, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.setattr(app_module, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(app_module, "NOTION_DB", str(tmp_path / "n.db"))
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


def a_text(client) -> str:
    items = client.get("/api/library?skill=lugemine&limit=1").json()["items"]
    assert items, "the fixture seeds one reading text"
    return items[0]["id"]


class TestOpeningATextRecordsIt:
    def test_exposure_is_written(self, client):
        client.get(f"/api/library/{a_text(client)}?minutes=3")
        got = exposure(progress_connect(app_module.PROGRESS_DB))
        assert got["items"] == 1
        assert got["minutes"] == 3.0

    def test_words_are_met(self, client):
        """Encounters, not knowledge: a word skimmed past is not a word
        learned, so this bumps a met-count and never promotes to known."""
        body = client.get(f"/api/library/{a_text(client)}").json()
        assert body["met_lemmas"] > 0

    def test_reading_counts_towards_the_reading_part(self, client):
        from eesti.sources import connect as content_connect

        from eesti import config

        client.get(f"/api/library/{a_text(client)}")
        got = parts_touched(progress_connect(app_module.PROGRESS_DB),
                            content_connect(config.CONTENT_DB))
        assert got.get("lugemine", 0) >= 1

    def test_a_missing_item_is_still_a_404(self, client):
        assert client.get("/api/library/does-not-exist").status_code == 404

    def test_bookkeeping_never_costs_the_learner_the_text(
        self, client, monkeypatch
    ):
        """If the progress database is unwritable, the reader still opens."""
        def explode(*args, **kwargs):
            raise OSError("disk gone")

        monkeypatch.setattr(app_module, "progress_db", explode)
        response = client.get(f"/api/library/{a_text(client)}")
        assert response.status_code == 200
        assert response.json()["body"]


class TestTheReadinessCountIsPerPart:
    def test_opening_a_listening_task_does_not_credit_reading(self, client):
        """`exposure` counts everything opened, so a learner who had only
        played listening tasks was credited with reading — the exact confusion
        the no-part-may-be-zero rule exists to punish."""
        listening = client.get(
            "/api/library?skill=kuulamine&limit=1").json()["items"]
        assert listening, "the fixture seeds one listening item"
        client.get(f"/api/library/{listening[0]['id']}")

        parts = {p["id"]: p for p in
                 client.get("/api/readiness/B1").json()["parts"]}
        assert parts["lugemine"]["touched"] is False
        assert "0 текстов" in parts["lugemine"]["evidence"]
