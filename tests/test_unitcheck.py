"""The unit check (`eesti/unitcheck.py`, ADR-0007): five server-graded items per
core topic and per revisited rule; a unit is complete when its core topics are
mastered and its check is passed.

What a learner would notice if these broke: a check that asks a topic the unit
does not teach, a pass the server did not grade, a perfect check that does not
count, a unit called complete that was never checked, a result lost on replay.
"""

from __future__ import annotations

import pytest

from eesti import units, unitcheck


def test_a_unit_checks_its_core_topics_and_its_revisits():
    kodus = units.by_id("kodus")
    parts = unitcheck.parts(kodus)
    assert ("kaskiv", None) in parts
    assert ("obj-case", ("imperative", "plural")) in parts


def test_a_topic_with_nothing_to_drill_is_not_asked():
    tutvume = unitcheck.parts(units.by_id("tutvume"))
    assert all(topic != "lauseehitus" for topic, _ in tutvume)


def test_a_revision_unit_with_a_checkpoint_runs_the_checkpoint():
    assert unitcheck.parts(units.by_id("reis")) == [("checkpoint:A2", None)]


def test_a_revision_unit_without_one_checks_its_stage_so_far():
    asked = {t for t, _ in unitcheck.parts(units.by_id("enesetunne"))}
    b1_before = {t for u in units.UNITS if u.stage == "B1" and u.n < 27 for t in u.topics}
    assert asked and asked <= b1_before


def test_the_same_seed_gives_the_same_items():
    """The server grades by rebuilding the set from its seed."""
    a = unitcheck.build(units.by_id("pere"), seed=7)
    b = unitcheck.build(units.by_id("pere"), seed=7)
    assert [(i.prompt, i.answer) for _, i in a] == [(i.prompt, i.answer) for _, i in b]
    assert {part for part, _ in a} == {("pohivormid", None), ("arvsonad", None)}
    assert all(sum(1 for p, _ in a if p == part) == unitcheck.PER_PART
               for part in {p for p, _ in a})


def _answers(unit, seed, wrong_in=None):
    out = []
    for part, item in unitcheck.build(unit, seed=seed):
        out.append("vale" if part[0] == wrong_in else item.answer.split(" ~ ")[0])
    return out


def test_all_right_passes_and_counts_its_topics_as_mastered(client):
    from eesti import config
    from eesti.progress import connect, mastered

    unit = units.by_id("pere")
    body = client.get("/api/units/pere/check?seed=3").json()
    assert body["items"] and body["parts"]
    r = client.post("/api/units/pere/check",
                    json={"seed": 3, "given": _answers(unit, 3)}).json()
    assert r["passed"]
    assert {"pohivormid", "arvsonad"} <= mastered(connect(config.PROGRESS_DB))
    state = {u["id"]: u for u in client.get("/api/curriculum").json()["units"]}["pere"]
    assert state["checked"] and state["complete"]


def test_a_part_below_four_of_five_fails_the_check_and_takes_nothing(client):
    unit = units.by_id("pere")
    r = client.post("/api/units/pere/check",
                    json={"seed": 4, "given": _answers(unit, 4, wrong_in="arvsonad")}).json()
    assert not r["passed"]
    parts = {p["topic"]: p for p in r["parts"]}
    assert parts["arvsonad"]["correct"] == 0 and parts["pohivormid"]["passed"]
    state = {u["id"]: u for u in client.get("/api/curriculum").json()["units"]}["pere"]
    assert not state["checked"] and not state["complete"]


def test_the_count_of_answers_must_match(client):
    r = client.post("/api/units/pere/check", json={"seed": 1, "given": ["a"]})
    assert r.status_code == 400


def test_an_unknown_unit_is_a_404(client):
    assert client.get("/api/units/nope/check").status_code == 404


def test_a_passed_check_survives_replay(tmp_path):
    """The result is an event; the projection is rebuilt from it."""
    from eesti import evidence
    from eesti.progress import connect

    progress = connect(tmp_path / "p.db")
    unitcheck.save(progress, "pere", [{"topic": "pohivormid", "rules": None,
                                        "asked": 5, "correct": 5}])
    assert unitcheck.passed_units(progress) == {"pere"}
    fresh = connect(tmp_path / "fresh.db")
    for ev in evidence.events(evidence.connect()):
        if ev.type == "unit-checked":
            evidence.apply({"progress": fresh}, ev)
    assert unitcheck.passed_units(fresh) == {"pere"}


@pytest.mark.parametrize("unit_id", [u.id for u in units.UNITS])
def test_every_unit_either_has_a_check_or_says_why_not(unit_id):
    unit = units.by_id(unit_id)
    parts = unitcheck.parts(unit)
    assert parts or unit.id in unitcheck.NO_CHECK, unit_id
