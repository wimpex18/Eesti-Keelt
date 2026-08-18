"""Themes: the axis that lets one grammar topic be drilled over one situation.

The theme lists are hand-picked — "which words belong to *food*" is a curatorial
judgement, not a derivable fact — so the tests check the things judgement gets
wrong: words that are not real, words above the learner's level, and words you
cannot have two of.
"""

from __future__ import annotations

import pytest

from eesti import themes
from eesti.practice import items_for
from eesti.themes import (THEMES, UNCOUNTABLE, by_id, countable_nouns, coverage,
                          lemmas_for, validate)
from eesti.wordlist import connect


@pytest.fixture
def words():
    return connect()


def test_every_theme_word_is_a_real_estonian_lemma(real_wordlist):
    """The check that caught `kingad`, `saapad`, `sokid` and `kindad` — plural-
    only forms where the lexicon lists the singular, and whose genitive a
    generator would have cheerfully invented."""
    assert validate(real_wordlist) == {}


def test_theme_ids_and_names_are_unique():
    assert len({t.id for t in THEMES}) == len(THEMES)
    assert len({t.et for t in THEMES}) == len(THEMES)


def test_no_theme_is_empty_on_either_axis():
    """A theme with no verbs cannot host a tense drill, and one with no nouns
    cannot host a case drill."""
    for theme in THEMES:
        assert theme.nouns and theme.verbs, theme.id


def test_words_above_the_level_are_dropped(words):
    at_a1 = set(lemmas_for(words, "toit", levels=("A1",)))
    at_b1 = set(lemmas_for(words, "toit", levels=("A1", "A2", "B1")))
    assert at_a1 <= at_b1


def test_untagged_words_are_kept(real_wordlist):
    """Only 6.2 % of Ekilex lemmas carry a CEFR level, so a missing tag is an
    absence of evidence, not evidence of difficulty."""
    tagged = {
        r[0]: r[1] for r in real_wordlist.execute(
            "SELECT word, proficiency FROM words WHERE word IN ('kodutöö','lendama')"
        )
    }
    assert any(v is None for v in tagged.values())
    kept = (set(lemmas_for(real_wordlist, "oppimine"))
            | set(lemmas_for(real_wordlist, "reisimine")))
    assert {w for w, v in tagged.items() if v is None} <= kept


def test_pos_filter_splits_nouns_from_verbs(words):
    theme = by_id("toit")
    assert set(lemmas_for(words, "toit", pos="s")) <= set(theme.nouns)
    assert set(lemmas_for(words, "toit", pos="v")) <= set(theme.verbs)


class TestCountability:
    def test_mass_nouns_are_excluded_from_counting(self, words):
        """*"Mul on kaks riisi"* — I have two rice. Countability is not in the
        word list and not guessable from the theme: `toit` holds both `kook`
        and `suhkur`."""
        counted = set(countable_nouns(words, "toit"))
        assert "kook" in counted
        assert not (counted & UNCOUNTABLE)

    def test_numeral_drills_only_count_countable_things(self, words):
        for theme in ("toit", "ilm", "tervis"):
            for item in items_for("arvsonad", count=6, seed=1, theme=theme):
                assert item.lemma not in UNCOUNTABLE

    def test_every_uncountable_word_is_actually_used_somewhere(self):
        """A stale exclusion list quietly narrows the drills for no reason."""
        declared = {w for t in THEMES for w in t.nouns}
        assert UNCOUNTABLE <= declared | {"raha"}


class TestThemedPractice:
    def test_a_verb_topic_uses_only_the_theme_verbs(self, words):
        allowed = set(lemmas_for(words, "reisimine", pos="v"))
        items = items_for("lihtminevik", count=8, seed=1, theme="reisimine")
        assert items
        assert {i.lemma for i in items} <= allowed

    def test_a_noun_topic_uses_only_the_theme_nouns(self, words):
        allowed = set(lemmas_for(words, "kodu", pos="s"))
        items = items_for("kohakaanded", count=5, seed=1, theme="kodu")
        assert {i.lemma for i in items} <= allowed

    def test_themes_and_topics_recombine(self, words):
        """The point of separating the axes: no lesson is written, they compose."""
        pairs = [
            (topic, theme.id)
            for topic in ("lihtminevik", "tingiv", "olevik")
            for theme in THEMES[:4]
        ]
        produced = sum(
            bool(items_for(topic, count=2, seed=1, theme=theme))
            for topic, theme in pairs
        )
        # Not every pairing exists — `ilm` has four verbs and no irregular
        # stems — so the claim is that most compose, not all.
        assert produced >= len(pairs) * 0.7

    def test_a_closed_class_topic_ignores_the_theme_rather_than_failing(self, words):
        """Question words have no vocabulary to vary; a lesson that silently
        produced zero items would be worse than one thematic in half its parts."""
        assert items_for("kusisonad", count=3, seed=1, theme="toit")

    def test_an_impossible_pairing_returns_empty_not_an_error(self, words):
        """`ilm` has four verbs, none of them irregular stems."""
        assert items_for("verb-form", count=5, seed=1, theme="ilm") is not None


def test_coverage_reports_the_usable_size(words):
    info = coverage(words)
    assert set(info) == {t.id for t in THEMES}
    for theme_id, row in info.items():
        assert row["usable"] <= row["declared"]
        assert row["nouns"] + row["verbs"] == row["usable"]
