"""The comma before a subordinate clause, and why this one may be generated.

`wordorder.py` refuses to generate its items: Estonian word order is flexible
enough that a swapped constituent is sometimes still correct, so a generated
distractor would teach the opposite of the rule. This module does the opposite
and generates, and the difference is a measurement rather than a preference.

Across 1 349 native texts, mid-sentence occurrences preceded by a comma:

    sest   99.0 %   et  95.9 %   |   nagu  63.9 %   kui  37.8 %

`kui` is also the comparative and `nagu` is also a preposition, so neither is a
rule. `et` and `sest` are, and every exception found was systematic — a
coordinating conjunction in front (`ja et`), a fixed collocation (`ilma et`,
`nii et`), or a sentence start. Excluding those, deleting the comma produces
Estonian that is provably wrong.
"""

from __future__ import annotations

import difflib
import sqlite3

import pytest

from eesti import punctuation


@pytest.fixture
def content(tmp_path):
    conn = sqlite3.connect(tmp_path / "content.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE items (id TEXT PRIMARY KEY, source_id TEXT, body TEXT);")
    bodies = [
        "Minister ütleb, et järgmisest aastast peab maksma rohkem.",
        "Ta jäi koju, sest ta oli haige.",
        "Ma arvan, et see on õige otsus meie jaoks.",
        # No comma is correct after a coordinating conjunction.
        "Ta tuli koju ja et kõik oleks korras, tegi ta süüa.",
        # `kui` is the comparative here — not a subordinate clause.
        "See maja on suurem kui teine maja meie tänaval.",
    ]
    conn.executemany("INSERT INTO items VALUES (?,?,?)",
                     [(str(i), "selges-keeles", b) for i, b in enumerate(bodies)])
    conn.commit()
    return conn


class TestOnlyTheCategoricalConjunctionsAreDrilled:
    def test_kui_and_nagu_are_not_offered(self):
        """At 38 % and 64 % they are not rules. Drilling them would teach a
        learner to insert commas into correct Estonian."""
        assert "kui" not in punctuation.CONJUNCTIONS
        assert "nagu" not in punctuation.CONJUNCTIONS

    def test_et_and_sest_are(self):
        assert set(punctuation.CONJUNCTIONS) == {"et", "sest"}

    def test_a_comparative_kui_produces_no_item(self, content):
        for item in punctuation.generate(count=20, seed=1, content=content):
            assert " kui " not in item.answer or "et" in item.conjunction

    def test_a_coordinating_conjunction_before_it_is_skipped(self):
        """`ja et`, `ning et`, `või et` take no comma — an item built from one
        would mark correct Estonian wrong."""
        assert punctuation._spans("Ta tuli ja et kõik oleks korras, tegi süüa.") == []

    def test_a_fixed_collocation_is_skipped(self):
        assert punctuation._spans("Ta tegi seda, ilma et keegi teaks.") == []
        assert punctuation._spans("Ta jooksis, nii et tolm keerles.") == []


class TestTheGeneratedPairIsSound:
    def test_the_two_choices_differ_by_exactly_one_comma(self, content):
        for item in punctuation.generate(count=20, seed=2, content=content):
            diff = [d for d in difflib.ndiff(item.answer, item.distractor)
                    if d[0] in "+-"]
            assert diff == ["- ,"], diff

    def test_the_right_answer_is_the_sentence_as_written(self, content):
        """The corpus punctuates correctly; the wrong version is the made-up
        one. Getting that backwards would drill the error."""
        bodies = " ".join(r[0] for r in content.execute("SELECT body FROM items"))
        for item in punctuation.generate(count=20, seed=3, content=content):
            assert item.answer in bodies

    def test_a_sentence_with_two_such_commas_is_refused(self):
        """Under a single deletion it would have two right answers and the
        learner could not tell which was being asked about."""
        two = ("Ma arvan, et see on õige, sest kõik teavad seda.")
        assert len(punctuation._spans(two)) == 2
        assert punctuation.from_sentences([two], count=5) == []

    def test_the_position_is_not_learnable(self, content):
        firsts = {punctuation.generate(count=1, seed=s, content=content)[0].choices[0]
                  for s in range(12)
                  if punctuation.generate(count=1, seed=s, content=content)}
        assert len(firsts) > 1

    def test_grading_is_the_shared_comparison(self, content):
        item = punctuation.generate(count=1, seed=4, content=content)[0]
        assert item.check(item.answer)
        assert not item.check(item.distractor)


class TestItReachesTheLearner:
    def test_the_topic_has_a_generator_now(self):
        from eesti.curriculum import by_id

        assert by_id("kirjavahemargid").generator == "punctuation"

    def test_the_explanation_is_in_russian(self):
        assert any("Ѐ" <= ch <= "ӿ" for ch in punctuation.WHY)

    def test_the_explanation_names_the_exceptions(self):
        """A rule stated without its exceptions is one the learner will
        over-apply — which is the failure this whole module is built to
        avoid."""
        assert "ilma et" in punctuation.WHY or "ja et" in punctuation.WHY

    def test_no_corpus_is_an_empty_list(self):
        assert punctuation.generate(count=3, content=None) == []
