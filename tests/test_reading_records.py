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

from eesti import app as app_module
from eesti import config as config_db
from eesti import config as _config  # noqa: E402
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
    monkeypatch.setattr(config_db, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(_config, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(config_db, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.setattr(_config, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.setattr(config_db, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(_config, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(config_db, "NOTION_DB", str(tmp_path / "n.db"))
    monkeypatch.setattr(_config, "NOTION_DB", str(tmp_path / "n.db"))
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


def a_text(client) -> str:
    items = client.get("/api/library?skill=lugemine&limit=1").json()["items"]
    assert items, "the fixture seeds one reading text"
    return items[0]["id"]


class TestOpeningATextRecordsIt:
    def test_exposure_is_written(self, client):
        client.get(f"/api/library/{a_text(client)}?minutes=3")
        got = exposure(progress_connect(config_db.PROGRESS_DB))
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
        got = parts_touched(progress_connect(config_db.PROGRESS_DB),
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


class TestTheRecommendationRanksRatherThanFilters:
    """A learner with 411 known words scores about 13 % coverage on the
    harvested news — nowhere near the 90 % instructional threshold. If that
    threshold were a filter, the *default* reading view would be empty for a
    real beginner, and an empty list cannot be told apart from an empty
    library.

    The docstring claimed a filter the code has never had. Fixed the docstring,
    not the code."""

    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        from fastapi.testclient import TestClient

        from eesti import app as app_module, config
        from eesti.sources import Item, add_items, connect, register

        path = tmp_path / "content.db"
        conn = connect(path)
        register(conn)
        add_items(conn, [
            Item(source_id="selges-keeles", skill="lugemine", title=f"Tekst {i}",
                 body="Ma elan Tallinnas ja töötan siin. Ta läks eile kooli.")
            for i in range(4)
        ])
        conn.commit()
        monkeypatch.setattr(config, "CONTENT_DB", str(path))
        monkeypatch.setattr(config_db, "VOCAB_DB", str(tmp_path / "v.db"))
        monkeypatch.setattr(_config, "VOCAB_DB", str(tmp_path / "v.db"))
        return TestClient(app_module.app)

    def test_texts_are_offered_even_when_none_clears_the_threshold(self, client):
        got = client.get("/api/reading/next?limit=5").json()
        assert got["items"], "the default view must not fail closed"
        assert all(i["coverage"] < got["threshold"] for i in got["items"])

    def test_the_band_says_the_text_is_hard_rather_than_hiding_it(self, client):
        got = client.get("/api/reading/next?limit=5").json()
        assert {i["readability"] for i in got["items"]} <= {"raske", "arendav",
                                                            "iseseisev"}

    def test_the_docstring_no_longer_claims_a_filter(self):
        from eesti.api.library import reading_next

        doc = reading_next.__doc__ or ""
        assert "It ranks; it does not filter." in doc

    def test_unmeasurable_is_reported_separately_from_empty(self, client):
        """"The library is empty" and "nothing could be measured" look
        identical in a list of length zero, and only one of them is the
        learner's problem."""
        got = client.get("/api/reading/next?limit=5").json()
        assert "unmeasurable" in got
