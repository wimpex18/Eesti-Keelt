"""Turning a word met while reading into scheduled practice.

A card that cannot be got wrong wastes review time, so a word with no case
contrast is not queued as a grammar card; if its meaning is known locally it
gets a `kind="vocab"` meaning card instead. Refused only when there is no
contrast and no known meaning.
"""

import pytest

from eesti import review
from eesti.mining import from_reading


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
        """The refusal names the real reason: not in the dictionary, no cases at all, or
        cases that coincide.
        """
        assert "перевод пока неизвестен" in from_reading(db, "kino").reason

    def test_it_does_not_claim_a_case_contrast_for_a_word_that_has_no_cases(self, db):
        """`kiiresti` is an adverb: it has no omastav and no osastav, so
        saying they coincide states something untrue about a word that has
        neither."""
        reason = from_reading(db, "kiiresti").reason
        assert "omastav" not in reason, reason

    @pytest.mark.parametrize("word", ["kino", "kiiresti", "zzzqqq"])
    def test_every_refusal_is_readable_by_the_learner(self, db, word):
        """Refusals are Russian (they render into the word card), for all three branches."""
        result = from_reading(db, word)
        assert not result.queued
        assert any("\u0400" <= ch <= "\u04ff" for ch in result.reason), result.reason

    def test_a_word_without_a_contrast_but_with_a_meaning_becomes_a_card(self, db):
        """`maja` (no contrast, glossed) becomes a meaning card; `kino` (no contrast, no
        gloss) is refused.
        """
        result = from_reading(db, "maja", context="See on suur maja.")
        assert result.queued, result.reason
        assert result.kind == "vocab"

        item = review.due(db)[0]
        assert item.lemma == "maja"
        assert "дом" in item.answer
        assert item.context == "See on suur maja."

    def test_the_meaning_card_uses_the_kind_the_schema_declared(self, db):
        """A meaning card is stored as `kind="vocab"`, the value the schema declares."""
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
