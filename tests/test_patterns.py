"""Comparison, numerals and question words.

The comparative rule is the risky one: genitive + `-m` is right often enough to
look reliable and wrong often enough to teach errors, so most of these tests are
about the gate that keeps the wrong ones out.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import patterns
from eesti.patterns import comparatives, comparison_drills, numeral_drills, question_drills


@pytest.fixture
def words(tmp_path):
    conn = sqlite3.connect(tmp_path / "w.db")
    conn.executescript(
        "CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INT,"
        " proficiency TEXT, pos TEXT);"
    )
    rows = [
        # adjectives whose comparative the rule gets right, and which are attested
        ("suur", 100, "A1", "adj"), ("suurem", 1160, None, "adj"),
        ("ilus", 200, "A1", "adj"), ("ilusam", 5000, None, "adj"),
        # the rule produces "vanam"; Estonian says "vanem", and "vanam" is not
        # in the lexicon at all
        ("vana", 300, "A1", "adj"),
        # the rule produces "omam", which Ekilex lists but nobody writes
        # (freq_rank 0) — the second gate is what catches this class
        ("oma", 400, "A1", "adj"), ("omam", 0, None, "adj"),
        ("raamat", 500, "A1", "s"), ("pilet", 600, "A1", "s"),
    ]
    conn.executemany("INSERT INTO words VALUES (?,?,?,?)", rows)
    conn.commit()
    return conn


class TestComparison:
    def test_a_correct_comparative_is_produced(self, words):
        assert ("suur", "suurem", "A1") in comparatives(words)

    def test_a_form_the_rule_gets_wrong_is_dropped(self, words):
        """genitive + -m gives *vanam*; Estonian says *vanem*. Not in the
        lexicon, so it never ships."""
        assert "vana" not in {p for p, _, _ in comparatives(words)}

    def test_a_form_nobody_writes_is_dropped(self, words):
        """*omam* is productively well-formed and Ekilex lists it, but its
        frequency rank is zero. Lexicon membership alone accepts too much."""
        assert "oma" not in {p for p, _, _ in comparatives(words)}

    def test_nouns_are_not_compared(self, words):
        assert "raamat" not in {p for p, _, _ in comparatives(words)}

    def test_the_superlative_is_kohige_plus_the_comparative(self, words):
        items = comparison_drills(words, count=20, seed=1)
        sup = [i for i in items if i.label_et == "ülivõrre"]
        assert sup
        for item in sup:
            assert item.answer.startswith("kõige ")
            # The lesson: `kõige` governs the comparative, not the positive.
            assert item.distractor.startswith("kõige ")
            assert item.answer != item.distractor

    def test_the_comparative_distractor_is_the_positive(self, words):
        items = [i for i in comparison_drills(words, count=20, seed=1)
                 if i.label_et == "keskvõrre"]
        assert items
        for item in items:
            assert item.distractor == item.lemma

    def test_an_empty_adjective_table_fails_loudly(self, tmp_path):
        conn = sqlite3.connect(tmp_path / "e.db")
        conn.executescript(
            "CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INT,"
            " proficiency TEXT, pos TEXT);"
        )
        with pytest.raises(RuntimeError, match="cli build"):
            comparison_drills(conn)


class TestNumerals:
    def test_a_cardinal_forces_the_partitive_singular(self, words):
        items = numeral_drills(words, count=5, seed=1, topics=("arvsonad",))
        assert items
        for item in items:
            assert item.topic == "arvsonad"
            # The error being trained against is the plural, which is what a
            # Russian speaker reaches for.
            assert item.answer != item.distractor

    def test_only_countable_nouns_are_counted(self, words):
        """Frequency order alone produced *"Mul on kaks tähelepanu"*: nothing in
        the word list marks countability."""
        from eesti.drills import POOLS

        countable = {w for pool in POOLS.values() for w in pool}
        for item in numeral_drills(words, count=5, seed=1, topics=("arvsonad",)):
            assert item.lemma in countable

    def test_ordinals_are_contrasted_with_their_own_cardinal(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(
            "CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INT,"
            " proficiency TEXT, pos TEXT);"
        )
        items = numeral_drills(conn, count=20, seed=1, topics=("jargarvud",))
        assert items
        by_lemma = {i.lemma: i for i in items}
        assert by_lemma["kolmas"].answer == "kolmandal"
        assert by_lemma["kolmas"].distractor == "kolmel"
        assert by_lemma["seitsmes"].answer == "seitsmendal"

    def test_every_ordinal_pair_is_a_real_pair(self):
        assert ("kolm", "kolmas") in patterns.ORDINALS
        assert len({c for c, _ in patterns.ORDINALS}) == len(patterns.ORDINALS)


class TestQuestionWords:
    def test_the_hint_does_not_contain_the_answer(self):
        """Here the word *is* the answer, unlike every other generator where the
        lemma is the given."""
        for item in question_drills(count=12, seed=1):
            assert item.answer.lower() not in item.hint.lower()
            assert item.hint == "küsisõna"

    def test_each_prompt_pairs_a_question_with_its_answer(self):
        for item in question_drills(count=12, seed=1):
            assert "—" in item.prompt
            assert item.prompt.startswith("____")

    def test_the_distractor_is_the_word_it_is_confused_with(self):
        pairs = {q.word: q.confused_with for q in patterns.QUESTIONS}
        assert pairs["Kus"] == "Kuhu" and pairs["Kes"] == "Mis"
        for item in question_drills(count=12, seed=1):
            assert item.distractor != item.answer

    def test_solution_capitalises_a_sentence_initial_answer(self):
        for item in question_drills(count=12, seed=1):
            assert item.solution[0].isupper()


def test_all_items_grade_deterministically(words):
    items = (
        comparison_drills(words, count=5, seed=1)
        + numeral_drills(words, count=5, seed=1)
        + question_drills(count=5, seed=1)
    )
    assert items
    for item in items:
        assert item.check(item.answer)
        assert item.check(f"  {item.answer.upper()}  ")
        assert not item.check(item.distractor)


def test_all_items_file_against_a_real_curriculum_topic(words):
    from eesti.curriculum import by_id

    items = (
        comparison_drills(words, count=5, seed=1)
        + numeral_drills(words, count=6, seed=1)
        + question_drills(count=5, seed=1)
    )
    for item in items:
        assert by_id(item.topic).generator == "patterns"


class TestSentenceSplittingDoesNotCutEstonianOrdinals:
    """`28. augustil` is "on the 28th of August", not two sentences. The
    splitter broke on every one, which put truncated sentences and orphaned
    tails into the corpus every generator draws on.

    The rule is not a digit special case: a sentence never *continues* with a
    lowercase word, so a period followed by one was never a boundary."""

    def split(self, text):
        from eesti.morph import split_sentences

        return split_sentences(text)

    def test_an_ordinal_does_not_end_a_sentence(self):
        assert len(self.split(
            "Maailmameister selgub pühapäeval, 28. augustil toimub festival.")) == 1

    def test_a_year_can_still_end_one(self):
        """`2018. Seal` is two sentences — the follower is capitalised."""
        assert len(self.split(
            "Õppuse nimi on Locked Shields 2018. Seal osales palju riike.")) == 2

    def test_ordinary_sentences_still_split(self):
        assert len(self.split("Ma elan siin. Ta läks kooli.")) == 2
        assert len(self.split("Kas sa tuled? Jah, tulen.")) == 2

    def test_a_closing_quote_does_not_hide_the_boundary(self):
        """Estonian writes „…” and ERR uses it constantly; the terminator is
        then not the last character before the space."""
        assert len(self.split("Ta ütles: „Ma tulen.” Siis läks ära.")) == 2
        assert len(self.split('Ta ütles: "Ma tulen." Siis läks ära.')) == 2

    def test_the_quote_survives_the_split(self):
        """Consuming it in the split pattern would have deleted it."""
        got = self.split("Ta ütles: „Ma tulen.” Siis läks ära.")
        assert "”" in got[0]
