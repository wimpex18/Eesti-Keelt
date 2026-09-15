"""Corpus cloze drills honour the level and serve easy sentences first.

`levels` gates the target word (a word tagged above the level is dropped), and
candidates are ordered by easiest sentence before the set is cut.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import cloze
from eesti.config import LEVELS


class TestTheTargetWordIsGatedByLevel:
    def test_a_word_the_list_calls_b2_is_dropped(self):
        assert cloze._above_level("B2", ("A1", "A2", "B1")) is True
        assert cloze._above_level("C1", ("A1", "A2", "B1")) is True

    def test_a_word_at_level_is_kept(self):
        for level in ("A1", "A2", "B1"):
            assert cloze._above_level(level, LEVELS) is False

    def test_an_untagged_word_is_kept(self):
        """A B2/C1 tag drops a word; no tag does not (most lemmas carry none)."""
        assert cloze._above_level(None, LEVELS) is False

    def test_b2_is_kept_when_b2_is_what_was_asked_for(self):
        assert cloze._above_level("B2", ("B1", "B2")) is False


class TestEaseOrdersAndNeverJudges:
    class _Tok:
        def __init__(self, lemma, pos="S"):
            self.lemma, self.pos = lemma, pos

    @pytest.fixture
    def words(self, tmp_path):
        conn = sqlite3.connect(tmp_path / "w.db")
        conn.execute("CREATE TABLE words (word TEXT PRIMARY KEY, "
                     "freq_rank INTEGER, proficiency TEXT, pos TEXT)")
        conn.executemany("INSERT INTO words VALUES (?,?,?,?)", [
            ("raamat", 1, "A1", "s"), ("kohv", 2, "A1", "s"),
            ("pilet", 3, "A2", "s"), ("hooldustöö", 4, "B2", "s"),
            ("riigivisiit", 5, None, "s"),
        ])
        conn.commit()
        return conn

    def test_an_easy_sentence_scores_higher(self, words):
        easy = [self._Tok("raamat"), self._Tok("kohv"), self._Tok("pilet")]
        hard = [self._Tok("hooldustöö"), self._Tok("riigivisiit"), self._Tok("kohv")]
        assert cloze._ease(words, easy) > cloze._ease(words, hard)

    def test_it_is_a_share_not_a_level(self, words):
        assert cloze._ease(words, [self._Tok("raamat"), self._Tok("hooldustöö")]) == 0.5

    def test_no_words_no_score_and_no_crash(self, words):
        assert cloze._ease(words, []) == 0.0

    def test_without_a_word_list_it_is_neutral(self):
        assert cloze._ease(None, [self._Tok("raamat")]) == 0.0

    def test_it_reads_content_words_only(self, words):
        """A sentence is not easier for containing more prepositions."""
        tokens = [self._Tok("raamat"), self._Tok("ja", pos="J"),
                  self._Tok("on", pos="V")]
        # `ja` is untagged and a conjunction; counting it would drag the score
        # down for a reason that has nothing to do with difficulty.
        assert cloze._ease(words, tokens) == 0.5

    def test_candidates_are_gathered_before_being_ranked(self):
        """More candidates are gathered than requested, so ordering has something to
        choose from.
        """
        assert cloze.OVERSAMPLE > 1


class TestAgainstTheRealCorpus:
    """On the real corpus, no target word is tagged above the requested levels."""

    @pytest.fixture(scope="class")
    @classmethod
    def fixtures(cls):
        from eesti import config
        from eesti.wordlist import connect

        content = sqlite3.connect(config.CONTENT_DB)
        content.row_factory = sqlite3.Row
        try:
            sents = cloze.sentences(content)
        except sqlite3.Error:
            pytest.skip("no content.db on this machine")
        if len(sents) < 200:
            pytest.skip("content.db has no corpus to draw on")
        return sents, connect()

    def test_no_item_targets_a_word_above_level(self, fixtures):
        sents, words = fixtures
        items = cloze.case_clozes(sents, topics=("osastav",), words=words,
                                  count=40, seed=1, levels=LEVELS)
        over = [i.lemma for i in items if i.level in ("B2", "C1", "C2")]
        assert not over, f"above-level targets reached a practice set: {over}"

    def test_a_set_is_easier_than_the_corpus_average(self, fixtures):
        """The ordering has to actually move the number, or it is decoration."""
        sents, words = fixtures
        from eesti.morph import analyze

        items = cloze.case_clozes(sents, topics=("osastav",), words=words,
                                  count=10, seed=2, levels=LEVELS)
        chosen = [cloze._ease(words, analyze(i.prompt)) for i in items]
        baseline = [cloze._ease(words, analyze(s)) for s in sents[:150]]
        assert sum(chosen) / len(chosen) > sum(baseline) / len(baseline)

    def test_negation_items_are_gated_too(self, fixtures):
        sents, words = fixtures
        items = cloze.negation_clozes(sents, words=words, count=40, seed=1,
                                      levels=LEVELS)
        assert not [i.lemma for i in items if i.level in ("B2", "C1", "C2")]

    def test_the_default_practice_call_honours_the_level(self):
        """The end of the chain: no theme, which is what the page sends."""
        from eesti import config
        from eesti.practice import items_for

        try:
            items = items_for("osastav", count=12, seed=3,
                              content_db=config.CONTENT_DB)
        except (sqlite3.Error, RuntimeError):
            pytest.skip("no content.db on this machine")
        if not items:
            pytest.skip("corpus not loaded")
        assert not [i for i in items if i.level in ("B2", "C1", "C2")]
