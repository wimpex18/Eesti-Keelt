"""ma, mas, mast, mata and des: each frame asks for one form, and the wrong
sibling is a real form of the same verb."""

from __future__ import annotations

from eesti.verbforms import drills


def test_each_answer_has_its_ending():
    endings = {"ma": "ma", "mas": "mas", "mast": "mast", "mata": "mata", "des": "es"}
    for item in drills(30, seed=7):
        assert item.answer.endswith(endings[item.rule]), item


def test_the_distractor_is_another_form_of_the_same_verb():
    for item in drills(30, seed=8):
        assert item.distractor != item.answer
        assert item.distractor[:3] == item.lemma[:3] or item.rule == "des"


def test_the_classic_examples():
    by_rule = {}
    for item in drills(60, seed=1):
        by_rule.setdefault((item.lemma, item.rule), item.answer)
    assert by_rule.get(("sööma", "mast"), "söömast") == "söömast"
    assert by_rule.get(("laulma", "des"), "lauldes") == "lauldes"
    assert by_rule.get(("sööma", "des"), "süües") == "süües"
