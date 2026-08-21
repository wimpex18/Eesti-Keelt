"""Spaced repetition scheduling.

The behaviours worth pinning are the ones that would silently corrupt a study
history: re-adding an item must not reset it, a wrong answer must bring the item
back sooner than a right one, and lapses must be counted so struggling items can
be surfaced.
"""

import sqlite3

import pytest

from eesti.review import (add, connect, due, grade, item_id,
                          repair_explanations, stats)


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


class TestExplanationsAlreadyInTheQueueAreRepaired:
    """A generator fix does not reach rows that were written before it.

    `omastav` was stored as **омастав** in the `why_ru` of every item the
    affected drills queued. Correcting `cloze.py` and `grammar.py` fixes what
    is generated next and nothing that is already scheduled -- and this is a
    spaced-repetition queue, so those items are not stale, they are guaranteed
    to come back and teach the wrong spelling again. Same shape as the seed
    glossary and the sonapi cache: state that outlives the process needs the
    fix applied where it sits.
    """

    def test_a_stored_transliteration_is_rewritten(self, tmp_path):
        db = tmp_path / "review.db"
        conn = connect(db)
        add(
            conn, kind="osastav", lemma="reegel", tag="sg p",
            prompt="Ma tean ____.", answer="reeglit", distractor="reegli",
            why_ru="**osastav** — частичный. Здесь *reeglit*, а не омастав *reegli*.",
        )
        conn.commit()
        conn.close()

        # A later process opens the same file: the repair runs on connect.
        conn = connect(db)
        why = conn.execute("SELECT why_ru FROM review_items").fetchone()[0]
        assert "омастав" not in why
        assert "**omastav**" in why

    def test_it_is_idempotent(self, tmp_path):
        """Running on every connect means it runs constantly. The replaced form
        must not itself match, or the text would grow on each open."""
        db = tmp_path / "review.db"
        conn = connect(db)
        add(
            conn, kind="mitmus", lemma="raamat", tag="pl n",
            prompt="____", answer="raamatud", distractor="raamat",
            why_ru="Множественное число строится от основы омастава.",
        )
        conn.commit()
        conn.close()

        connect(db).close()
        conn = connect(db)
        why = conn.execute("SELECT why_ru FROM review_items").fetchone()[0]
        assert why == "Множественное число строится от основы генитива (omastav)."
        assert repair_explanations(conn) == 0

    def test_untouched_rows_are_left_alone(self, tmp_path):
        db = tmp_path / "review.db"
        conn = connect(db)
        add(conn, kind="osastav", lemma="kass", tag="sg p",
                   prompt="____", answer="kassi", distractor="kass",
                   why_ru="**osastav** — частичный.")
        conn.commit()
        assert repair_explanations(conn) == 0

    def test_it_does_not_write_when_there_is_nothing_to_repair(self, tmp_path):
        """Running on every `connect` is only safe if the common case is a
        read. The first version issued the UPDATE unconditionally, which made
        every open of the queue a writer -- including the read-only ones behind
        `GET /api/status` -- and the next connection got `database is locked`.
        """
        db = tmp_path / "review.db"
        conn = connect(db)
        add(conn, kind="osastav", lemma="kass", tag="sg p", prompt="____",
            answer="kassi", distractor="kass", why_ru="**osastav** — частичный.")
        conn.commit()
        conn.close()

        conn = connect(db)
        writes = []
        conn.set_trace_callback(
            lambda sql: writes.append(sql) if sql.lstrip()[:6].upper() in
            ("UPDATE", "INSERT", "DELETE") else None)
        assert repair_explanations(conn) == 0
        assert not writes, f"repair wrote to a clean queue: {writes}"
