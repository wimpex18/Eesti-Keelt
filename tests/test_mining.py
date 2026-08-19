"""Turning encounters into scheduled practice.

The rule under test throughout: an item that cannot be got wrong must not be
queued. Review time is the scarcest resource in spaced repetition, and a card
with no contrast spends it for nothing.
"""

import pytest

from eesti import review
from eesti.mining import from_failed_drill, from_reading


@pytest.fixture()
def db(tmp_path):
    return review.connect(tmp_path / "review.db")


class TestMiningFromReading:
    def test_a_word_with_a_contrast_is_queued_with_its_sentence(self, db):
        result = from_reading(db, "raamatut", context="Ma lugesin raamatu läbi.")
        assert result.queued and result.kind == "obj-case"

        item = review.due(db)[0]
        assert item.lemma == "raamat"
        # Context is the whole point of mining from reading rather than a list.
        assert item.context == "Ma lugesin raamatu läbi."

    def test_a_word_without_a_contrast_is_refused_with_a_reason(self, db):
        """`kino` has genitive == partitive, so there is nothing to drill."""
        result = from_reading(db, "kino")
        assert not result.queued
        assert "samad" in result.reason
        assert review.due(db) == []

    def test_an_unknown_word_is_refused(self, db):
        result = from_reading(db, "zzzqqq")
        assert not result.queued
        assert not review.due(db)

    def test_mining_the_same_word_twice_does_not_duplicate(self, db):
        from_reading(db, "raamatut", context="esimene lause")
        from_reading(db, "raamatut", context="teine lause")
        assert db.execute("SELECT COUNT(*) FROM review_items").fetchone()[0] == 1


class TestMiningFromFailedDrills:
    def test_a_wrong_answer_enters_the_queue_already_marked_missed(self, db):
        """It must not look like fresh material — it was just got wrong."""
        result = from_failed_drill(
            db, lemma="minema", prompt="Ma ____ kooli.", answer="lähen",
            distractor="minen", rule="verb-form",
        )
        assert result.queued and result.kind == "verb-form"

        row = db.execute(
            "SELECT reps, lapses FROM review_items WHERE id = ?", (result.item_id,)
        ).fetchone()
        assert row["reps"] == 1 and row["lapses"] == 1

    def test_object_case_rules_map_to_the_obj_case_kind(self, db):
        for rule in ("completed", "ongoing", "negation"):
            result = from_failed_drill(
                db, lemma=f"test{rule}", prompt="___", answer="a",
                distractor="b", rule=rule,
            )
            assert result.kind == "obj-case"
