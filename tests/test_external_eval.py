"""The grammar_et scoring track.

The delicate part is deciding which pairs are scorable at all. Positional
alignment reads a word swap as a cascade of bogus substitutions, and scoring a
model against those would punish it for not making changes that were never
corrections.
"""

import pytest

from eesti.evals.external import MAX_CHANGES, changed_tokens


class TestScorablePairs:
    def test_a_single_substitution_is_scorable(self):
        assert changed_tokens(
            "Selle uuringu käigul selgus.", "Selle uuringu käigus selgus."
        ) == {"käigul": "käigus"}

    def test_two_substitutions_are_scorable(self):
        assert changed_tokens(
            "on vaja ülikoolid, mis annavad inimesteid.",
            "on vaja ülikoole, mis annavad inimesi.",
        ) == {"ülikoolid,": "ülikoole,", "inimesteid.": "inimesi."}

    def test_word_reordering_is_not_a_correction(self):
        """A swap aligns as two substitutions, neither of which is a fix."""
        assert changed_tokens("kuhu tuleb rahvas", "kuhu rahvas tuleb") == {}

    def test_reordering_hidden_by_punctuation_is_also_rejected(self):
        """`lõpeb` and `lõpeb.` are the same word wearing a full stop."""
        assert changed_tokens("see varsti lõpeb.", "see lõpeb varsti.") == {}

    def test_length_changes_are_skipped(self):
        assert changed_tokens("ma lugesin", "ma lugesin raamatu") == {}

    def test_wholesale_rewrites_are_skipped(self):
        """Beyond a couple of changes it is a rewrite, not a targeted error."""
        original = "aaa bbb ccc ddd"
        rewrite = "www xxx yyy zzz"
        assert len(rewrite.split()) == len(original.split())
        assert changed_tokens(original, rewrite) == {}

    def test_the_change_limit_is_respected(self):
        two = changed_tokens("aa bb cc", "xx yy cc")
        assert len(two) <= MAX_CHANGES and two == {"aa": "xx", "bb": "yy"}


def test_the_corpus_yields_a_usable_number_of_scorable_pairs():
    """Guards the filters: too strict and the track measures nothing."""
    external = pytest.importorskip("eesti.evals.external")
    try:
        rows = external.load()
    except FileNotFoundError:
        pytest.skip("run `python -m eesti.cli fetch-bench` first")

    scorable = [r for r in rows if changed_tokens(r["original"], r["correct"])]
    assert len(scorable) >= 150, f"only {len(scorable)} scorable pairs"
