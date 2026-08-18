"""Regression set for the #1 documented gap: total (genitive) vs partial
(partitive) object.

Two halves, and the second matters as much as the first: the tool must catch
planted errors AND stay quiet on correct partitives. A checker that flags every
partitive would "pass" the first half while teaching exactly the wrong rule.

Runs fully offline via Vabamorf — no API keys, no network, so it can gate every
change.
"""

import pytest

from eesti.morph import (
    analyze,
    case_forms,
    has_distinct_object_cases,
    object_case_candidates,
)

# (lemma, genitive, partitive) — hand-checked reference forms.
KNOWN_FORMS = [
    ("raamat", "raamatu", "raamatut"),
    ("auto", "auto", "autot"),
    ("pilet", "pileti", "piletit"),
    ("laud", "laua", "lauda"),
    ("sõber", "sõbra", "sõpra"),   # consonant gradation
    ("pood", "poe", "poodi"),      # irregular stem
    ("tuba", "toa", "tuba"),
    ("leib", "leiva", "leiba"),
    ("töö", "töö", "tööd"),
]

# Words where the two cases coincide: no drill is possible, and the tool must
# not pretend otherwise.
IDENTICAL_CASES = ["maja", "kool", "õun", "kiri", "film"]


@pytest.mark.parametrize("lemma,genitive,partitive", KNOWN_FORMS)
def test_case_forms_match_reference(lemma, genitive, partitive):
    forms = case_forms(lemma)
    assert forms.get("genitive") == genitive, f"{lemma} genitive"
    assert forms.get("partitive") == partitive, f"{lemma} partitive"


@pytest.mark.parametrize("lemma", IDENTICAL_CASES)
def test_identical_cases_are_not_drillable(lemma):
    forms = case_forms(lemma)
    assert forms["genitive"] == forms["partitive"]
    assert not has_distinct_object_cases(lemma)


@pytest.mark.parametrize(
    "sentence,word,expected_form",
    [
        # Planted errors: partitive used where a completed action needs genitive.
        ("Ma lugesin raamatut läbi.", "raamatut", "sg p"),
        ("Ma ostsin uut autot.", "autot", "sg p"),
        ("Ma sõin õunat ära.", "õunat", "sg p"),
        # Correct genitives, which must be recognised as genitive.
        ("Ma lugesin raamatu läbi.", "raamatu", "sg g"),
        ("Ma ostsin uue auto.", "auto", "sg g"),
    ],
)
def test_detector_reads_the_right_case(sentence, word, expected_form):
    """Vabamorf must report the case actually written — that is the evidence the
    grammar provider adjudicates on."""
    match = [t for t in analyze(sentence) if t.text == word]
    assert match, f"{word!r} not found in {sentence!r}"
    assert match[0].form == expected_form


@pytest.mark.parametrize(
    "sentence",
    [
        "Ma lugesin raamatut läbi.",
        "Ma ostsin uut autot.",
        "Ma lugesin raamatu läbi.",
    ],
)
def test_candidates_are_surfaced(sentence):
    """Every sentence with an object in genitive/partitive yields a candidate."""
    assert object_case_candidates(sentence), f"no candidate in {sentence!r}"


@pytest.mark.parametrize(
    "sentence",
    [
        "Ma jooksin pargis.",          # intransitive, no object at all
        "Ta magab kodus.",
        "Me elame Tallinnas.",
    ],
)
def test_no_false_candidates_without_objects(sentence):
    """Sentences with no object must not produce object-case candidates.

    This is the false-positive guard: over-flagging would teach the wrong rule.
    """
    assert object_case_candidates(sentence) == []


class TestVerbForms:
    """Irregular verb stems — the secondary documented gap (`verb-form`).

    The design claim under test: the naive form (strip -ma, add the ending) is
    the error a learner actually makes, so it is the right distractor. These
    check that claim holds for the verbs the drills lean on hardest.
    """

    @pytest.mark.parametrize(
        "lemma,tag,actual,naive",
        [
            ("minema", "n", "lähen", "minen"),      # the canonical example
            ("minema", "sin", "läksin", "minesin"),
            ("minema", "da", "minna", "mineda"),
            ("olema", "b", "on", "oleb"),
            ("tegema", "sin", "tegin", "tegesin"),
            ("nägema", "n", "näen", "nägen"),
            ("sööma", "sin", "sõin", "söösin"),
        ],
    )
    def test_naive_form_is_the_real_mistake(self, lemma, tag, actual, naive):
        from eesti.verbs import forms_for, naive_form

        match = [f for f in forms_for(lemma) if f.tag == tag]
        assert match, f"{lemma} has no {tag} form"
        form = match[0]
        assert form.actual == actual
        assert naive_form(lemma, tag) == naive
        assert form.is_irregular

    def test_regular_verbs_are_excluded(self):
        """A verb the naive rule gets right teaches nothing and must not appear."""
        from eesti.verbs import forms_for

        regular = [f for f in forms_for("elama") if f.tag == "n"]
        assert regular and regular[0].actual == "elan"
        assert not regular[0].is_irregular

    def test_generated_verb_drills_are_answerable(self):
        from eesti.drills import generate_verb_drills
        from eesti.wordlist import connect

        drills = generate_verb_drills(connect(), count=12, seed=1)
        assert len(drills) == 12
        for drill in drills:
            assert drill.rule == "verb-form"
            # The whole point: answer and distractor must differ, or the item
            # cannot be got wrong and measures nothing.
            assert drill.answer.lower() != drill.distractor.lower()
            assert drill.check(drill.answer)
            assert not drill.check(drill.distractor)
