"""Checked material in the app: serving, answering, *Teata veast*, retiring (ADR-0009, step 5)."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from test_material import material, words  # noqa: F401  (fixture)


@pytest.fixture
def built(words, tmp_path, monkeypatch):  # noqa: F811
    """The fixture dialogue, stamped, checked and built into a scratch content.db."""
    from eesti import config
    from eesti.material import store
    from eesti.sources import connect

    root = tmp_path / "material"
    store.write_checked(store.stamp(material(), engine="claude-haiku-5-5", batch="b"), root)
    path = tmp_path / "content.db"
    conn = connect(path)
    ids, refused = store.build(conn, words, root)
    conn.close()
    assert not refused and len(ids) == 1
    monkeypatch.setattr(config, "CONTENT_DB", path)
    return ids[0]


def shared() -> sqlite3.Connection:
    from eesti import config

    return sqlite3.connect(config.PROGRESS_DB)


def learner(n: int):
    return SimpleNamespace(kind="learner", id=f"l-{n:016x}")


GUEST = SimpleNamespace(kind="guest", id="sandbox")
OWNER = SimpleNamespace(kind="owner", id="owner")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestRetiring:
    def test_answers_that_split_retire_the_item(self):
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        why = None
        for i in range(stats.SPLIT_MIN):
            other = i % 3 == 0          # a third give the same other answer
            why = stats.record_answer(conn, "m", "q1", correct=not other,
                                      answer="kolm eurot" if other else "neli eurot",
                                      permanent=True)
        assert why and why.startswith("answers split")

    def test_scattered_wrong_answers_do_not_split(self):
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        others = iter(("üks", "kaks", "kolm", "viis", "kuus", "seitse", "kaheksa"))
        for i in range(stats.SPLIT_MIN):
            stats.record_answer(conn, "m", "q1", correct=i % 3 != 0,
                                answer=next(others) if i % 3 == 0 else "neli eurot",
                                permanent=True)
        assert stats.retired(conn, "m") == {}

    def test_an_item_everyone_gets_right_is_retired(self):
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        for _ in range(stats.STEADY_MIN):
            stats.record_answer(conn, "m", "q1", correct=True, answer="x", permanent=True)
        assert stats.retired(conn, "m")["q1"].startswith("never varies")

    def test_guests_answers_never_retire(self):
        """A sandbox is a name anyone can choose."""
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        for _ in range(stats.STEADY_MIN * 2):
            stats.record_answer(conn, "m", "q1", correct=True, answer="x", permanent=False)
        assert stats.retired(conn, "m") == {}

    def test_two_peoples_reports_retire_one_persons_do_not(self):
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        for _ in range(3):
            assert stats.record_report(conn, "m", "q1", reason="mitu-vastust", note="",
                                       scope=learner(1)) is None
        assert stats.record_report(conn, "m", "q1", reason="mitu-vastust", note="",
                                   scope=learner(2)) == "reported by 2 people"

    def test_the_owners_report_retires_at_once(self):
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        assert stats.record_report(conn, "m", "", reason="viga-tekstis", note="",
                                   scope=OWNER) == "reported by the owner"
        assert stats.WHOLE in stats.retired(conn, "m")

    def test_guests_reports_are_kept_and_never_retire(self):
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        for n in range(5):
            stats.record_report(conn, "m", "q1", reason="muu", note="",
                                scope=SimpleNamespace(kind="guest", id=f"g{n}"))
        assert stats.retired(conn, "m") == {}
        assert stats.summary(conn)[0]["reports"] == 5

    def test_retiring_is_sticky(self):
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        for _ in range(stats.STEADY_MIN):
            stats.record_answer(conn, "m", "q1", correct=True, answer="x", permanent=True)
        stats.record_answer(conn, "m", "q1", correct=False, answer="y", permanent=True)
        assert "q1" in stats.retired(conn, "m")

    def test_no_learners_words_are_kept(self):
        """An answer is a hash; a reporter is a hash; a note is capped."""
        from eesti.material import stats

        conn = stats.ready(sqlite3.connect(":memory:"))
        stats.record_answer(conn, "m", "q1", correct=False, answer="minu salajane vastus",
                            permanent=True)
        stats.record_report(conn, "m", "q1", reason="muu", note="x" * 5000,
                            scope=learner(7))
        dump = "\n".join(conn.iterdump())
        assert "salajane" not in dump and learner(7).id not in dump
        assert conn.execute("SELECT length(note) FROM material_reports").fetchone() == (
            stats.NOTE_CHARS,)

    def test_an_unknown_reason_is_refused(self):
        from eesti.material import stats

        with pytest.raises(ValueError):
            stats.record_report(sqlite3.connect(":memory:"), "m", "", reason="x",
                                note="", scope=OWNER)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class TestTheRoutes:
    def test_a_unit_without_material_serves_none(self, client):
        assert client.get("/api/material/units/kohvik").json() == {
            "unit": "kohvik", "material": []}

    def test_an_unknown_unit_is_404(self, client):
        assert client.get("/api/material/units/nope").status_code == 404

    def test_the_unit_serves_its_material_without_keys(self, client, built):
        got = client.get("/api/material/units/kohvik").json()
        [m] = got["material"]
        assert m["id"] == built and m["kind"] == "dialoog"
        assert m["turns"][0] == {"speaker": "Mari", "text": "Tere! Mida te soovite?"}
        assert m["label"].startswith("написано моделью")
        assert m["engine"] == "hand-written test fixture"
        assert m["off_list"] == [{"lemma": "kook", "gloss_ru": "пирог"}]
        assert all(set(q) == {"id", "question"} for q in m["questions"])
        assert m["gaps"] == [{"id": "g1",
                              "prompt": "Juhan: Tere! Üks kohv ja kaks ___, palun. (sai, osastav)"}]

    def test_an_answer_is_graded_by_code_against_the_key(self, client, built):
        right = client.post("/api/material/answer", json={
            "material": built, "item": "q1", "answer": "Ta soovib kaks saia."}).json()
        assert right["correct"] is True and right["retired"] is False
        wrong = client.post("/api/material/answer", json={
            "material": built, "item": "q1", "answer": "kolm"}).json()
        assert wrong["correct"] is False and "kaks saia" in wrong["why_ru"]

    def test_a_gap_is_graded_by_its_word(self, client, built):
        assert client.post("/api/material/answer", json={
            "material": built, "item": "g1", "answer": "saia"}).json()["correct"]
        miss = client.post("/api/material/answer", json={
            "material": built, "item": "g1", "answer": "sai"}).json()
        assert not miss["correct"] and "osastav" in miss["why_ru"]

    def test_an_answer_is_reading_practice_in_the_log(self, client, built):
        from eesti import evidence

        client.post("/api/material/answer", json={
            "material": built, "item": "q2", "answer": "neli eurot"})
        with evidence.connect() as log:
            [row] = log.execute(
                "SELECT payload FROM events WHERE type = 'comprehension'").fetchall()
        import json

        payload = json.loads(row["payload"])
        assert payload["item"] == built and payload["expected"] == "neli eurot"
        assert payload["question"] == "Mis maksab kokku?" and payload["correct"]

    def test_an_answer_is_counted_in_the_shared_store(self, client, built):
        client.post("/api/material/answer", json={
            "material": built, "item": "q1", "answer": "kaks saia"})
        with shared() as conn:
            assert conn.execute("SELECT COUNT(*) FROM material_answers").fetchone() == (1,)

    def test_unknown_material_and_items_are_404(self, client, built):
        assert client.post("/api/material/answer", json={
            "material": "mat:kohvik:x@00000000", "item": "q1", "answer": ""}).status_code == 404
        assert client.post("/api/material/answer", json={
            "material": built, "item": "q9", "answer": ""}).status_code == 404

    def test_teata_veast_retires_and_the_item_is_no_longer_served(self, client, built):
        got = client.post("/api/material/report", json={
            "material": built, "item": "q3", "reason": "mitu-vastust",
            "note": "Mari küsib ka muud."}).json()
        assert got == {"recorded": True, "retired": True}   # the owner's report
        [m] = client.get("/api/material/units/kohvik").json()["material"]
        assert "q3" not in [q["id"] for q in m["questions"]]

    def test_a_report_on_the_whole_text_withdraws_it(self, client, built):
        client.post("/api/material/report", json={
            "material": built, "reason": "viga-tekstis"})
        assert client.get("/api/material/units/kohvik").json()["material"] == []

    def test_a_guests_report_is_recorded_and_retires_nothing(self, client, built):
        got = client.post("/api/material/report", headers={"x-eesti-scope": "guest",
                                                            "x-eesti-guest": "agent-test"},
                          json={"material": built, "item": "q3", "reason": "muu"}).json()
        assert got == {"recorded": True, "retired": False}

    def test_a_guest_reads_the_material(self, client, built):
        got = client.get("/api/material/units/kohvik",
                         headers={"x-eesti-scope": "guest", "x-eesti-guest": "agent-test"})
        assert [m["id"] for m in got.json()["material"]] == [built]

    def test_a_report_needs_a_known_reason_and_item(self, client, built):
        assert client.post("/api/material/report", json={
            "material": built, "reason": "x"}).status_code == 422
        assert client.post("/api/material/report", json={
            "material": built, "item": "q9", "reason": "muu"}).status_code == 404

    def test_the_library_lists_the_text_as_public_reading(self, client, built):
        """Built as a library item under a public source, for every learner."""
        got = client.get(f"/api/library/{built}",
                         headers={"x-eesti-scope": "guest", "x-eesti-guest": "agent-test"})
        assert got.status_code == 200
