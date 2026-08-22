"""Turning encounters into scheduled practice.

The rule under test throughout: an item that cannot be got wrong must not be
queued. Review time is the scarcest resource in spaced repetition, and a card
with no contrast spends it for nothing.

That rule is about the *grammar* card, and it used to be applied to every word.
A noun whose genitive and partitive are identical has no contrast to drill --
and 31.3 % of A1-B1 words are in that position (791 of 2 531; A1 35.8 %, A2
34.9 %, B1 28.5 %). All of them were refused with "pole midagi harjutada",
which told a learner there was nothing to practise about a word they had just
clicked *because they did not know it*.

They have a meaning, and the app now knows what most of those meanings are. So
the fallback is a `kind="vocab"` card -- the kind `review.py`'s schema has
documented since it was written and which nothing had ever produced. The
refusal survives for the case that is genuinely empty: no contrast **and** no
known meaning.
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

    def test_a_word_without_a_contrast_or_a_meaning_is_refused(self, db):
        """`kino` has genitive == partitive and is not in the gloss store, so
        there is genuinely nothing to put on a card."""
        result = from_reading(db, "kino")
        assert not result.queued
        assert "omastav" in result.reason
        assert review.due(db) == []

    def test_the_refusal_says_which_of_the_two_reasons_applies(self, db):
        """Every refusal used to read "omastav ja osastav on samad", including
        the ones that were really "we do not know what this word means yet" --
        so the learner was told the word had nothing to teach when the truth
        was that the app had nothing to say about it."""
        assert "перевод пока неизвестен" in from_reading(db, "kino").reason

    def test_it_does_not_claim_a_case_contrast_for_a_word_that_has_no_cases(self, db):
        """`kiiresti` is an adverb: it has no omastav and no osastav, so
        saying they coincide states something untrue about a word that has
        neither."""
        reason = from_reading(db, "kiiresti").reason
        assert "omastav" not in reason, reason

    @pytest.mark.parametrize("word", ["kino", "kiiresti", "zzzqqq"])
    def test_every_refusal_is_readable_by_the_learner(self, db, word):
        """A refusal renders straight into the word card via `r.reason`, so it
        is an explanation, and the language rule puts explanations in Russian.

        `test_ui_language` only ever scanned `index.html`, so nothing here was
        checked at all -- and every one of these three was Estonian. Covering
        the three branches rather than one: not in the dictionary, no cases at
        all, and cases that coincide."""
        result = from_reading(db, word)
        assert not result.queued
        assert any("\u0400" <= ch <= "\u04ff" for ch in result.reason), result.reason

    def test_a_word_without_a_contrast_but_with_a_meaning_becomes_a_card(self, db):
        """`maja`: genitive and partitive are both `maja`, so no contrast --
        but it means something, and that is worth a review.

        `maja` and `kino` are the pair the fixture already carries for the
        no-contrast case, and they differ in exactly the way that now matters:
        one is in the shipped glossary and the other is not."""
        result = from_reading(db, "maja", context="See on suur maja.")
        assert result.queued, result.reason
        assert result.kind == "vocab"

        item = review.due(db)[0]
        assert item.lemma == "maja"
        assert "дом" in item.answer
        assert item.context == "See on suur maja."

    def test_the_meaning_card_uses_the_kind_the_schema_declared(self, db):
        """`review_items.kind` has said "curriculum topic id, or `vocab`" since
        it was written, and nothing had ever written a `vocab` row."""
        from_reading(db, "maja")
        kinds = {r[0] for r in db.execute("SELECT kind FROM review_items")}
        assert kinds == {"vocab"}

    def test_it_does_not_reach_the_network_for_a_meaning(self, db, monkeypatch):
        """`gloss.remember` is the one call allowed to leave the machine, and it
        belongs to the word card where the learner is already waiting on it --
        not behind a click that should feel instant."""
        import eesti.gloss as gl

        def explode(*a, **k):  # pragma: no cover - the point is it is not hit
            raise AssertionError("mining fetched a gloss over the network")

        monkeypatch.setattr(gl, "remember", explode)
        assert from_reading(db, "maja").queued

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
