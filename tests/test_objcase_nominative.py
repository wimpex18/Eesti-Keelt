"""The nominative total object: the half of `obj-case` a learner trained only on
"completed → omastav" gets wrong (*Osta leiva ära!*).

EKK SÜ 40 and the EKI Teatmik (*Täissihitise kääne*) give four conditions for a
nominative total object: a plural object, a command, the impersonal, and an object
of a *da*-infinitive that is not itself another verb's object. Its exception keeps
the genitive (*pere otsustas kutsika võtta*). Forms come from Vabamorf.
"""

from __future__ import annotations

import pytest

from eesti.drills import BASE_RULES, LABEL_ET, RULE_ET, TEMPLATES, generate
from eesti.morph import analyze, unique_form

NOMINATIVE_RULES = ("imperative", "impersonal", "infinitive", "plural")


@pytest.fixture
def words(fixture_data):
    from eesti.wordlist import connect

    return connect(fixture_data["words"])


@pytest.mark.parametrize("lemma,tag,form", [
    ("leib", "sg n", "leib"),
    ("leib", "pl n", "leivad"),
    ("leib", "pl g", "leibade"),
    ("raamat", "pl n", "raamatud"),
    ("raamat", "pl g", "raamatute"),
    ("võti", "pl n", "võtmed"),
])
def test_forms_are_vabamorfs_and_read_back(lemma, tag, form):
    assert unique_form(lemma, tag) == form


@pytest.mark.parametrize("lemma", ["kool", "reis"])
def test_a_word_with_two_paradigms_has_no_key(lemma):
    """`kool` and `reis` have two genitives; one key would be a guess."""
    assert unique_form(lemma, "sg g") is None


def test_the_default_set_keeps_the_genitive_partitive_contrast(words):
    """A set without rules is what mastery, test-out and placement draw: it must
    not change under learners who are working towards the gate."""
    items = generate(words, count=30, seed=4)
    assert {d.rule for d in items} <= set(BASE_RULES)
    assert {d.case for d in items} <= {"genitive", "partitive"}


def test_imperative_takes_the_nominative(words):
    items = generate(words, count=10, seed=1, rules=("imperative",))
    assert items
    for d in items:
        assert d.case == "nominative" and d.label == "nimetav"
        assert d.answer == unique_form(d.lemma, "sg n")
        assert d.distractor == unique_form(d.lemma, "sg g")
        assert d.answer != d.distractor
        assert d.prompt.rstrip().endswith("!")


def test_impersonal_takes_the_nominative(words):
    items = generate(words, count=10, seed=2, rules=("impersonal",))
    assert items
    for d in items:
        assert d.case == "nominative"
        assert d.distractor == unique_form(d.lemma, "sg g")
        verbs = [t for t in analyze(d.prompt.replace("____", "")) if t.pos == "V"]
        assert any(t.form in ("ti", "takse", "tud", "tavat") for t in verbs), d.prompt


def test_infinitive_separates_tuleb_from_tahan(words):
    """*Tuleb leib ära osta* (nominative), but *Ma tahan leiva ära osta*: there the
    infinitive is itself the object of *tahtma* (Teatmik's exception)."""
    items = generate(words, count=24, seed=3, rules=("infinitive",))
    cases = {d.case for d in items}
    assert cases == {"nominative", "genitive"}
    for d in items:
        governed = any(w in d.prompt.split() for w in ("tahan", "otsustasin", "tahtsin"))
        assert d.case == ("genitive" if governed else "nominative"), d.prompt
        assert {d.answer, d.distractor} == {unique_form(d.lemma, "sg n"),
                                            unique_form(d.lemma, "sg g")}


def test_plural_total_object_is_nominative_plural(words):
    items = generate(words, count=10, seed=5, rules=("plural",))
    assert items
    for d in items:
        assert d.case == "nominative" and d.number == "pl"
        assert d.label == "mitmuse nimetav"
        assert d.answer == unique_form(d.lemma, "pl n")
        assert d.distractor == unique_form(d.lemma, "pl g")
        # The frame itself asks for a plural, or a typed answer could not know.
        assert "kõik" in d.prompt.split()


def test_a_nominative_item_is_a_choice(words):
    """Typed, *Osta leivad ära!* is Estonian too; the base contrast keeps its
    first-sight choice only, as before."""
    for rule in NOMINATIVE_RULES:
        for d in generate(words, count=6, seed=7, rules=(rule,)):
            assert set(d.choices) == {d.answer, d.distractor}
    assert all(not d.choices for d in generate(words, count=10, seed=7))


def test_a_word_whose_nominative_is_its_genitive_is_not_asked(words):
    """`auto`: nominative and genitive coincide, so the contrast cannot be got wrong."""
    for rule in NOMINATIVE_RULES:
        for d in generate(words, count=20, seed=6, rules=(rule,)):
            assert d.answer != d.distractor
            assert not (d.number == "sg" and d.lemma in ("auto", "arvuti"))


def test_every_frame_is_estonian_vabamorf_knows():
    """A frame's own words must be real forms: a misspelt verb would teach it.
    Read without guessing, which would give any string a lemma."""
    from eesti.morph import parts_of_speech, tokenize

    for tpl in TEMPLATES:
        unknown = [w for w in tokenize(tpl.frame.format(obj="raamat"))
                   if w.isalpha() and not parts_of_speech(w)]
        assert not unknown, (tpl.frame, unknown)


def test_every_rule_has_an_estonian_name():
    """Planning names a weak rule by `RULE_ET`; a bare id would print a key."""
    assert {t.rule for t in TEMPLATES} <= set(RULE_ET)
    assert LABEL_ET["nominative"] == "nimetav"


def test_the_api_serves_nominative_items_and_grades_them(client):
    items = client.post("/api/practice", json={
        "topic": "obj-case", "count": 6, "seed": 2, "rules": ["imperative"],
    }).json()["items"]
    assert items and {it["form_after"] for it in items} == {"nimetav"}
    item = items[0]
    right = client.post("/api/practice/answer", json={
        "topic": "obj-case", "prompt": item["prompt"], "answer": item["answer"],
        "given": item["answer"], "token": item["token"], "record": False}).json()
    wrong = client.post("/api/practice/answer", json={
        "topic": "obj-case", "prompt": item["prompt"], "answer": item["answer"],
        "given": item["distractor"], "token": item["token"], "record": False}).json()
    assert right["correct"] and not wrong["correct"]
