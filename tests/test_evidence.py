"""The evidence log is the source of truth: the learner databases are projections
of it, rebuilt by replay, and the log moves between instances by event id.
"""

from __future__ import annotations

import sqlite3

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import config, evidence  # noqa: E402

STATE = {"x-state-token": "s3cret"}


@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient

    from eesti.app import app

    monkeypatch.setenv("STATE_TOKEN", "s3cret")
    return TestClient(app)


def _projections() -> dict[str, list[tuple]]:
    """Every projection row, minus columns that are not learner facts."""
    out = {}
    paths = {"progress": config.PROGRESS_DB, "review": config.REVIEW_DB,
             "vocab": config.VOCAB_DB, "notion": config.NOTION_DB}
    for db, tables in evidence.PROJECTIONS.items():
        conn = sqlite3.connect(paths[db])
        for table in tables:
            try:
                out[f"{db}.{table}"] = sorted(
                    tuple(r) for r in conn.execute(f"SELECT * FROM {table}"))
            except sqlite3.OperationalError:
                out[f"{db}.{table}"] = []
        conn.close()
    return out


def _a_card() -> str:
    """A card id straight from the queue's table: a miss is due again only in
    minutes, so `/api/review` (due cards) does not list it yet."""
    conn = sqlite3.connect(config.REVIEW_DB)
    try:
        return conn.execute("SELECT id FROM review_items ORDER BY rowid").fetchone()[0]
    finally:
        conn.close()


def _work(client) -> None:
    """A little of everything a learner does."""
    items = client.post("/api/practice", json={"topic": "obj-case", "count": 4}).json()["items"]
    for n, it in enumerate(items):
        client.post("/api/practice/answer", json={
            "topic": "obj-case", "prompt": "", "answer": "", "given":
                it["answer"] if n % 2 else "vale", "token": it["token"],
                "latency_ms": 2000})
    client.post("/api/review/grade", json={"id": _a_card(), "given": "vale"})
    client.post("/api/vocab/known", json={"lemmas": ["raamat"]})
    client.post("/api/checkpoint/A1/result", json={"asked": 10, "correct": 9})


class TestReplay:
    def test_a_rebuild_reproduces_every_projection(self, client):
        _work(client)
        before = _projections()
        assert before["progress.attempts"] and before["review.review_items"]
        with evidence.connect() as conn:
            evidence.rebuild(conn)
        assert _projections() == before

    def test_a_fresh_instance_rebuilds_from_the_imported_log(self, client, tmp_path,
                                                             monkeypatch):
        _work(client)
        before = _projections()
        log = client.get("/api/events?limit=2000", headers=STATE).json()["events"]

        # A new container: empty paths for every learner database and the log.
        for name in ("PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB", "EVENTS_DB"):
            monkeypatch.setattr(config, name, str(tmp_path / f"{name}.db"))
        r = client.post("/api/events/import", headers=STATE,
                        json={"events": log, "settle": True}).json()
        assert r["added"] == len(log) and r["settled"]["rebuilt"] == len(log)
        assert _projections() == before

    def test_importing_the_same_events_twice_changes_nothing(self, client):
        _work(client)
        log = client.get("/api/events?limit=2000", headers=STATE).json()["events"]
        again = client.post("/api/events/import", headers=STATE,
                            json={"events": log}).json()
        assert again["added"] == 0


class TestBackfill:
    def test_rows_from_before_the_log_enter_it_once(self, tmp_path):
        from eesti import progress, vocab

        conn = progress.connect(config.PROGRESS_DB)
        conn.execute("INSERT INTO attempts (topic,item_key,correct,answer,at)"
                     " VALUES ('tingiv','k1',1,'x','2026-01-01T00:00:00+00:00')")
        conn.commit()
        vocab.connect(config.VOCAB_DB).close()
        with evidence.connect() as log:
            assert evidence.backfill(log) == 1
            evidence.backfill(log)  # a second backfill of the same rows
            legacy = [e for e in evidence.events(log) if e.type == "legacy-row"]
        assert len(legacy) == 1

    def test_the_first_event_backfills_what_came_before(self):
        from eesti import progress

        conn = progress.connect(config.PROGRESS_DB)
        conn.execute("INSERT INTO attempts (topic,item_key,correct,answer,at)"
                     " VALUES ('tingiv','k1',0,'x','2026-01-01T00:00:00+00:00')")
        conn.commit()
        progress.mark_mastered(conn, "tingiv", via="placement")
        with evidence.connect() as log:
            types = [e.type for e in evidence.events(log)]
        assert types == ["legacy-row", "backfill", "mastered"]


class TestSignedItems:
    def test_the_server_grades_what_it_issued_not_what_the_page_says(self, client):
        it = client.post("/api/practice", json={"topic": "tingiv", "count": 1}).json()["items"][0]
        # The page claims its wrong answer is the key; the token says otherwise.
        r = client.post("/api/practice/answer", json={
            "topic": "tingiv", "prompt": it["prompt"], "answer": "vale",
            "given": "vale", "token": it["token"]}).json()
        assert r["correct"] is False and r["answer"] == it["answer"]

    def test_a_tampered_token_is_refused(self, client):
        it = client.post("/api/practice", json={"topic": "tingiv", "count": 1}).json()["items"][0]
        body, mac = it["token"].rsplit(".", 1)
        forged = body + "." + ("0" * len(mac))
        r = client.post("/api/practice/answer", json={
            "topic": "tingiv", "prompt": "", "answer": "", "given": "x", "token": forged})
        assert r.status_code == 400

    @pytest.mark.parametrize("topic", ["tingiv", "obj-case", "kusisonad", "lihtminevik"])
    def test_a_ref_regenerates_its_item(self, client, topic):
        from eesti.itemref import regenerate, verify

        items = client.post("/api/practice", json={"topic": topic, "count": 5}).json()["items"]
        for it in items:
            issued = verify(it["token"])
            again = regenerate(issued["ref"])
            assert (again.prompt, again.answer) == (it["prompt"], it["answer"])

    def test_a_checkpoint_ref_regenerates_its_item(self, client):
        from eesti.itemref import regenerate, verify

        items = client.get("/api/checkpoint/A1?count=6").json()["items"]
        assert items
        for it in items:
            again = regenerate(verify(it["token"])["ref"])
            assert (again.prompt, again.answer) == (it["prompt"], it["answer"])

    def test_the_attempt_event_carries_the_ref_and_the_item(self, client):
        it = client.post("/api/practice", json={"topic": "tingiv", "count": 1}).json()["items"][0]
        client.post("/api/practice/answer", json={
            "topic": "tingiv", "prompt": "", "answer": "", "given": it["answer"],
            "token": it["token"], "latency_ms": 1234})
        with evidence.connect() as log:
            ev = [e for e in evidence.events(log) if e.type == "attempt"][-1]
        assert ev.payload["ref"]["kind"] == "practice"
        assert ev.payload["expected"] == it["answer"]
        assert ev.payload["latency_ms"] == 1234 and ev.payload["correct"] is True


class TestAutoRating:
    def test_a_typed_review_answer_is_rated_by_code(self, client):
        it = client.post("/api/practice", json={"topic": "tingiv", "count": 1}).json()["items"][0]
        client.post("/api/practice/answer", json={
            "topic": "tingiv", "prompt": "", "answer": "", "given": "vale",
            "token": it["token"]})
        r = client.post("/api/review/grade", json={
            "id": _a_card(), "given": it["answer"], "latency_ms": 60_000}).json()
        assert r["correct"] and r["rating"] == "hard"
        with evidence.connect() as log:
            ev = [e for e in evidence.events(log) if e.type == "review"][-1]
        assert ev.payload["auto"] is True and ev.payload["rating"] == "hard"

    def test_rating_and_answer_are_not_both_accepted(self, client):
        r = client.post("/api/review/grade", json={"id": "x", "rating": "good", "given": "y"})
        assert r.status_code == 400

    @pytest.mark.parametrize("correct,latency,rating", [
        (False, None, "again"), (True, None, "good"), (True, 1000, "good"),
        (True, 20_000, "hard"),
    ])
    def test_auto_rating(self, correct, latency, rating):
        from eesti.review import auto_rating

        assert auto_rating(correct, latency) == rating

    def test_a_correct_answer_on_a_due_card_is_its_review(self, client):
        it = client.post("/api/practice", json={"topic": "tingiv", "count": 1}).json()["items"][0]
        miss = {"topic": "tingiv", "prompt": "", "answer": "", "token": it["token"]}
        client.post("/api/practice/answer", json=miss | {"given": "vale"})
        # The miss is rated Again, so the card is due again within minutes;
        # jump past that and answer right.
        from datetime import datetime, timedelta, timezone

        from eesti import review

        conn = review.connect(config.REVIEW_DB)
        later = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        conn.execute("UPDATE review_items SET due = ?", (later,))
        conn.commit()
        client.post("/api/practice/answer", json=miss | {"given": it["answer"]})
        with evidence.connect() as log:
            reviews = [e.payload for e in evidence.events(log) if e.type == "review"]
        assert [r["rating"] for r in reviews] == ["again", "good"]
        assert reviews[-1]["auto"] is True


class TestExport:
    def test_the_learner_can_download_the_log(self, client):
        client.post("/api/vocab/known", json={"lemmas": ["raamat"]})
        r = client.get("/api/me/export")
        assert r.status_code == 200
        assert "word-status" in r.text and r.text.endswith("\n")

    def test_the_log_routes_need_the_state_token(self, client):
        assert client.get("/api/events").status_code == 403
        assert client.post("/api/events/import", json={}).status_code == 403

    def test_responses_say_how_far_the_log_has_got(self, client):
        client.post("/api/vocab/known", json={"lemmas": ["raamat"]})
        r = client.get("/api/health")
        assert int(r.headers["x-events-seq"]) >= 1


class TestPracticeOutsideDrills:
    """Writing and speaking leave evidence of practice, never graded evidence."""

    def test_a_writing_check_is_recorded(self, client):
        client.post("/api/check", json={"text": "Ma lähen kooli."})
        with evidence.connect() as log:
            ev = [e for e in evidence.events(log) if e.type == "writing"][-1]
        assert ev.payload["text"] == "Ma lähen kooli." and ev.payload["words"] == 3

    def test_an_open_spoken_answer_is_recorded_with_its_length(self, client):
        r = client.post("/api/speaking/feedback", json={
            "transcript": "Ma elan Tallinnas", "question": "Kus sa elad?",
            "seconds": 3.0}).json()
        assert r["pace_wpm"] == 60.0
        with evidence.connect() as log:
            ev = [e for e in evidence.events(log) if e.type == "speech"][-1]
        assert ev.payload["kind"] == "open" and ev.payload["seconds"] == 3.0

    def test_a_read_aloud_is_recorded_without_audio(self, client):
        client.post("/api/transcribe/text?target=Ma%20loen", json={
            "text": "Ma loen", "engine": "test"})
        with evidence.connect() as log:
            ev = [e for e in evidence.events(log) if e.type == "speech"][-1]
        assert ev.payload["kind"] == "read-aloud"
        assert ev.payload["matched"] == ev.payload["total"] == 2
        assert "audio" not in ev.payload

    def test_log_only_events_replay_to_nothing(self, client):
        client.post("/api/check", json={"text": "Tere."})
        with evidence.connect() as conn:
            evidence.rebuild(conn)
