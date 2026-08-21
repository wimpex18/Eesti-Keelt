"""Two A1 topics that were in the syllabus and opened nothing.

`pohivormid` and `eitus` carried `generator=None`, so a beginner who reached
them -- both are A1, both are prerequisites for topics that *are* drilled --
got a message saying nothing would happen.

Both generate offline, from the wordlist and Vabamorf, with no harvested
corpus. That is deliberate: the corpus generators produce nothing on a fresh
deployment, and these are the first topics anybody meets.

The tests that matter here are the two that caught real defects:

  * the answer was printed in its own prompt for 41 of 480 items, because the
    nominative frequently equals the genitive or the partitive and only the
    genitive/partitive pair is guaranteed distinct;
  * the connegative is neither the da-infinitive nor the imperative.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti.forms import (connegative, negation_drills, past_participle,
                         principal_forms)


@pytest.fixture
def words(tmp_path):
    conn = sqlite3.connect(tmp_path / "w.db")
    conn.executescript("""
        CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INTEGER,
                            proficiency TEXT, pos TEXT);
        CREATE TABLE object_cases (word TEXT PRIMARY KEY, genitive TEXT NOT NULL,
                            partitive TEXT NOT NULL, distinct_ INTEGER NOT NULL);
    """)
    conn.executemany("INSERT INTO words VALUES (?,?,?,?)", [
        ("raamat", 100, "A1", "s"),
        ("linnapea", 200, "A2", "s"),     # nominative == genitive
        ("maja", 50, "A1", "s"),          # no contrast at all
        ("ostma", 60, "A1", "v"),
        ("minema", 30, "A1", "v"),        # suppletive: the interesting one
        ("olema", 10, "A1", "v"),
    ])
    conn.executemany("INSERT INTO object_cases VALUES (?,?,?,?)", [
        ("raamat", "raamatu", "raamatut", 1),
        ("linnapea", "linnapea", "linnapead", 1),
        ("maja", "maja", "maja", 0),
    ])
    conn.commit()
    return conn


class TestPrincipalForms:
    def test_the_answer_is_never_printed_in_its_own_prompt(self, words):
        """`distinct_` guarantees genitive != partitive and says nothing about
        the nominative, which often equals one of them -- `linnapea, linnapea,
        linnapead`. Asking for a form shown beside the blank lets the learner
        copy it across and score a correct answer for a question they were
        given. 41 of 480 generated items did exactly that."""
        for seed in range(30):
            for item in principal_forms(words, count=10, seed=seed):
                shown = [p for p in item.prompt.replace("____", "").split(", ") if p]
                assert item.answer not in shown, item.prompt

    def test_a_word_with_no_contrast_is_never_drilled(self, words):
        """`maja, maja, maja` asks the learner to type the word back at itself."""
        got = {i.lemma for seed in range(20)
               for i in principal_forms(words, count=10, seed=seed)}
        assert "maja" not in got

    def test_all_three_forms_get_asked(self, words):
        asked = {i.label for seed in range(30)
                 for i in principal_forms(words, count=10, seed=seed)}
        assert asked == {"nimetav", "omastav", "osastav"}

    def test_grading_is_exact_and_needs_no_network(self, words, monkeypatch):
        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (
            _ for _ in ()).throw(AssertionError("grading went to the network")))
        item = principal_forms(words, count=1, seed=0)[0]
        assert item.check(item.answer)
        assert item.check(f"  {item.answer.upper()} ")   # trimmed, casefolded
        assert not item.check(item.distractor)

    def test_the_explanation_is_in_russian(self, words):
        """The rule this project states first: explanations are Russian."""
        for item in principal_forms(words, count=6, seed=1):
            assert any("Ѐ" <= ch <= "ӿ" for ch in item.why_ru)


class TestTheConnegative:
    @pytest.mark.parametrize("verb,expected", [
        ("ostma", "osta"),
        ("olema", "ole"),
        ("tulema", "tule"),
        ("tegema", "tee"),
        ("nägema", "näe"),
        # The one that decides the derivation. The da-infinitive gives `minna`
        # and the imperative gives `mine`; Estonian says `ma ei lähe`.
        ("minema", "lähe"),
    ])
    def test_it_is_the_present_stem(self, verb, expected):
        assert connegative(verb) == expected

    def test_it_is_not_the_da_infinitive(self):
        from eesti.morph import synthesize
        assert list(synthesize("minema", "da"))[0] == "minna"
        assert connegative("minema") != "minna"

    def test_it_is_not_the_imperative(self):
        from eesti.morph import synthesize
        assert list(synthesize("minema", "o"))[0] == "mine"
        assert connegative("minema") != "mine"

    def test_an_unanalysable_word_is_skipped_not_guessed(self):
        assert connegative("zzzqqq") is None

    @pytest.mark.parametrize("verb,expected", [
        ("ostma", "ostnud"), ("minema", "läinud"), ("tegema", "teinud")])
    def test_the_past_takes_the_nud_participle(self, verb, expected):
        assert past_participle(verb) == expected


class TestNegationDrills:
    def test_the_distractor_is_the_affirmative(self, words):
        """The error being drilled is carrying the inflected verb across the
        negation -- *ei ostan* -- which is what Russian's `не` allows."""
        for item in negation_drills(words, count=6, seed=2):
            assert item.distractor != item.answer

    def test_the_affirmative_is_graded_wrong(self, words):
        for item in negation_drills(words, count=6, seed=2):
            assert item.check(item.answer)
            assert not item.check(item.distractor)

    def test_both_tenses_are_produced(self, words):
        labels = {i.label for seed in range(25)
                  for i in negation_drills(words, count=8, seed=seed)}
        assert labels == {"eitus olevik", "eitus minevik"}

    def test_the_explanation_names_the_contrast_with_russian(self, words):
        found = [i for seed in range(10)
                 for i in negation_drills(words, count=8, seed=seed)
                 if i.label == "eitus olevik"]
        assert found
        assert any("русск" in i.why_ru for i in found)


class TestBothAreReachableThroughTheCurriculum:
    @pytest.mark.parametrize("topic", ["eitus", "pohivormid"])
    def test_the_topic_has_a_generator_now(self, topic):
        from eesti.curriculum import by_id
        assert by_id(topic).generator == "forms"

    @pytest.mark.parametrize("topic", ["eitus", "pohivormid"])
    def test_practice_no_longer_refuses_the_topic(self, topic):
        """The regression being guarded is the refusal, not the yield.

        `items_for` used to raise `ValueError: 'eitus' has no generator`, which
        the API turned into a 400 and the page printed as `Viga: ...`. It must
        now dispatch.

        It is deliberately not asserted that items come *back*: the shared
        fixture wordlist carries no `object_cases` rows, so `pohivormid` has
        nothing to build from there, and a test that demanded output would be
        asserting on fixture contents rather than on this code. What the
        generators produce is covered above, against a connection with known
        rows in it.
        """
        from eesti.practice import items_for

        assert isinstance(items_for(topic, count=3), list)
