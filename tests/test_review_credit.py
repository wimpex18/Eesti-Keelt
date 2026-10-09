"""EKI's credit follows an item into the review queue.

An item built from EKI EVS's phrases carries its credit on the page; missed, it
becomes a card, and the card must still say whose sentence it is (CC BY 4.0 asks
for the credit wherever the material is shown). Cards queued before the credit
travelled replay unchanged and show none.
"""

from __future__ import annotations

from dataclasses import dataclass

from eesti import evs, itemref


@dataclass(frozen=True)
class _Phrase:
    """The fields an issued item signs (`itemref.FIELDS`)."""

    topic: str = "osastav"
    prompt: str = "ma joon ____ hommikul"
    answer: str = "kohvi"
    distractor: str = "kohv"
    lemma: str = "kohv"
    hint: str = "kohv, osastav"
    rule: str = "osastav"
    why_ru: str = "Часть количества → osastav."
    source_id: str = evs.SOURCE_ID


def _due_now() -> None:
    """A missed card returns minutes later; move it to now, as the clock would."""
    from eesti import config, review

    conn = review.connect(config.learner_db("REVIEW_DB"))
    with conn:
        conn.execute("UPDATE review_items SET due = '2000-01-01T00:00:00+00:00'")


def _ref() -> dict:
    return itemref.practice_ref("osastav", seed=1, count=1, levels=["A1"],
                                theme=None, rules=None, index=0)


def test_a_missed_evs_item_becomes_a_credited_card(client):
    token = itemref.sign(_Phrase(), _ref())
    r = client.post("/api/practice/answer", json={
        "topic": "osastav", "prompt": "x", "answer": "x", "given": "kohv",
        "token": token})
    assert r.status_code == 200 and not r.json()["correct"]
    _due_now()
    cards = client.get("/api/review?kind=osastav").json()["items"]
    card = next(c for c in cards if c["lemma"] == "kohv")
    assert card["attribution"] == evs.ATTRIBUTION


def test_an_item_without_a_source_makes_an_uncredited_card(client):
    token = itemref.sign(_Phrase(source_id=""), _ref())
    client.post("/api/practice/answer", json={
        "topic": "osastav", "prompt": "x", "answer": "x", "given": "kohv",
        "token": token})
    _due_now()
    card = client.get("/api/review?kind=osastav").json()["items"][0]
    assert not card.get("attribution")


def test_a_card_queued_before_the_credit_replays(tmp_path):
    """An old `card-added` event has no `source_id`: replay writes the card."""
    from eesti import review

    conn = review.connect(tmp_path / "r.db")
    review._add(conn, {"kind": "osastav", "lemma": "kohv", "tag": "osastav",
                       "prompt": "p", "answer": "kohvi", "distractor": "kohv",
                       "why_ru": None, "source": "practice", "context": None},
                "2026-10-01T00:00:00+00:00")
    [card] = review.due(conn, limit=5)
    assert card.lemma == "kohv" and card.source_id is None


def test_a_queue_made_before_the_credit_gains_the_column(tmp_path):
    """An existing review database has no `source_id` column; opening it adds
    one, and its cards stay."""
    import sqlite3

    from eesti import review

    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.executescript(review.SCHEMA.replace(
        "    source_id   TEXT,               -- the material's registry id, for its credit\n", ""))
    assert "source_id" not in {r[1] for r in conn.execute("PRAGMA table_info(review_items)")}
    conn.close()
    reopened = review.connect(old)
    assert "source_id" in {r[1] for r in reopened.execute("PRAGMA table_info(review_items)")}


def test_an_old_token_without_a_source_still_grades(client):
    """Answers queued offline carry tokens signed before `source_id` was signed."""
    payload = {"ref": _ref(), "item": {k: getattr(_Phrase(), k) for k in
                                       itemref.FIELDS if k not in ("source_id", "say")}}
    token = itemref._sign(payload)
    r = client.post("/api/practice/answer", json={
        "topic": "osastav", "prompt": "x", "answer": "x", "given": "kohvi",
        "token": token, "record": False})
    assert r.status_code == 200 and r.json()["correct"]
