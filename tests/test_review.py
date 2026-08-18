"""Spaced repetition scheduling.

The behaviours worth pinning are the ones that would silently corrupt a study
history: re-adding an item must not reset it, a wrong answer must bring the item
back sooner than a right one, and lapses must be counted so struggling items can
be surfaced.
"""

import pytest

from eesti.review import add, connect, due, grade, item_id, stats


@pytest.fixture()
def db(tmp_path):
    return connect(tmp_path / "review.db")


def _seed(conn, kind="obj-case", lemma="raamat", tag="completed"):
    return add(
        conn, kind=kind, lemma=lemma, tag=tag,
        prompt="Ma lugesin ____ läbi.", answer="raamatu",
        distractor="raamatut", why_ru="завершено → omastav",
        source="reading", context="Ma lugesin selle raamatu läbi.",
    )


def test_new_items_are_due_immediately(db):
    _seed(db)
    assert [i.lemma for i in due(db)] == ["raamat"]


def test_readding_keeps_the_existing_schedule(db):
    """Meeting a word again must not wipe the memory model built for it."""
    key = _seed(db)
    grade(db, key, "good")
    scheduled = db.execute(
        "SELECT due, reps FROM review_items WHERE id = ?", (key,)
    ).fetchone()

    assert _seed(db) == key          # same id, no duplicate row
    after = db.execute(
        "SELECT due, reps FROM review_items WHERE id = ?", (key,)
    ).fetchone()
    assert after["due"] == scheduled["due"]
    assert after["reps"] == scheduled["reps"] == 1
    assert db.execute("SELECT COUNT(*) FROM review_items").fetchone()[0] == 1


def test_wrong_answers_come_back_sooner_than_right_ones(db):
    wrong = add(db, kind="verb-form", lemma="minema", tag="n",
                prompt="Ma ____ kooli.", answer="lähen", distractor="minen")
    right = add(db, kind="verb-form", lemma="tegema", tag="n",
                prompt="Ma ____ tööd.", answer="teen", distractor="tegen")

    lapsed = grade(db, wrong, "again")
    passed = grade(db, right, "good")
    assert lapsed["interval_days"] < passed["interval_days"]
    assert lapsed["lapses"] == 1 and passed["lapses"] == 0


def test_struggling_items_are_surfaced(db):
    key = _seed(db)
    for _ in range(3):
        grade(db, key, "again")
    report = stats(db)
    assert report["total"] == 1
    assert report["struggling"][0]["lemma"] == "raamat"
    assert report["struggling"][0]["lapses"] == 3


def test_unknown_item_and_bad_rating_are_rejected(db):
    with pytest.raises(KeyError):
        grade(db, "nope:nope:", "good")
    key = _seed(db)
    with pytest.raises(ValueError):
        grade(db, key, "brilliant")


def test_item_id_is_stable(db):
    assert item_id("obj-case", "raamat", "completed") == "obj-case:raamat:completed"
