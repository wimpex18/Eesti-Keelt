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
