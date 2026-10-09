"""The B1-first exam loop (ADR-0009): exam-day rules from HARNO's sheet, both
writing tasks with a code checklist, and practice from a mock's misses.

What a learner would notice if these broke: an exam-day rule HARNO does not
state; a writing task the exam does not set; a content point counted as
covered when the text never mentions it; a letter without a greeting passing
unremarked; a missed reading item with no way to practise its rule.
"""

from __future__ import annotations

import pytest

from eesti import writingtasks
from eesti.examday import EXAM_DAY, SOURCE


def test_the_exam_day_rules_cite_harno_s_sheet():
    """Each fact here is on HARNO's examinee information sheet."""
    assert SOURCE.startswith("https://harno.ee/")
    joined = " ".join(EXAM_DAY).casefold()
    for fact in ("10.00", "id-карта", "водительские права", "60%", "40 дней", "45%"):
        assert fact in joined, fact


def test_the_spec_carries_the_day_and_its_level_timing(client):
    b1 = client.get("/api/exam-spec/B1").json()
    a2 = client.get("/api/exam-spec/A2").json()
    assert b1["exam_day"]["source"] == SOURCE
    assert any("35" in rule for rule in b1["exam_day"]["rules"])
    assert any("30" in rule for rule in a2["exam_day"]["rules"])


@pytest.mark.parametrize("level,tasks", [("B1", {1: {"teade", "kusimustik"},
                                                  2: {"jutt", "kiri"}}),
                                          ("A2", {1: {"visiitkaart"},
                                                  2: {"teade", "loovtekst"}})])
def test_each_level_sets_harno_s_two_tasks_and_their_variants(level, tasks):
    """HARNO: B1 task 1 is a questionnaire or a note, task 2 a story or a personal
    letter; A2 task 1 transfers a business card, task 2 a note or a creative text."""
    got = {}
    for t in writingtasks.BANK[level]:
        got.setdefault(t.task_no, set()).add(t.kind)
    assert got == tasks


def test_every_prompt_is_estonian_vabamorf_knows():
    """A prompt is model-written (labelled): its words must at least be real."""
    from eesti.morph import parts_of_speech, tokenize

    for level, bank in writingtasks.BANK.items():
        for t in bank:
            # The card is data (names, an address, an e-mail), not prose.
            text = " ".join([t.prompt_et, *t.questions])
            unknown = [w for w in tokenize(text) if w.isalpha() and w[0].islower()
                       and not parts_of_speech(w)]
            assert not unknown, (t.id, unknown)


def _task(level, kind):
    return next(t for t in writingtasks.BANK[level] if t.kind == kind)


def test_a_point_counts_only_when_the_text_carries_it():
    note = _task("B1", "teade")
    covered = writingtasks.check(note, "Tere! Ma ei saa homme tulla, sest ma olen haige. "
                                      "Saame kokku laupäeval kell kuus kohvikusse.")
    blank = writingtasks.check(note, "Tere! Mul on hea tuju. Ilm on ilus.")
    assert all(p["found"] for p in covered["points"])
    assert not any(p["found"] for p in blank["points"])


def test_a_letter_names_a_missing_greeting_and_closing():
    letter = _task("B1", "kiri")
    bare = writingtasks.check(letter, "Ma elan nüüd Tartus ja töötan poes. " * 6)
    framed = writingtasks.check(
        letter, "Kallis Mari!\n" + "Ma elan nüüd Tartus ja töötan poes. " * 6 +
        "\nParimate soovidega\nAnna")
    assert not bare["opening"] and not bare["closing"]
    assert framed["opening"] and framed["closing"]


def test_length_is_measured_against_harno_s_figure():
    story = _task("B1", "jutt")
    short = writingtasks.check(story, "Eile ma käisin poes.")
    assert short["words"] == 4 and not short["long_enough"]
    assert short["target_words"] == 100


def test_the_questionnaire_needs_all_ten_answers():
    form = _task("B1", "kusimustik")
    assert len(form.questions) == 10
    half = writingtasks.check(form, "", answers=["Ma elan Tallinnas."] * 5 + [""] * 5)
    assert half["answered"] == 5 and not half["long_enough"]


def test_the_mock_writes_both_tasks_and_records_them(client):
    section = client.get("/api/mock/B1/kirjutamine?seed=2").json()
    assert section["minutes"] == 35 and len(section["tasks"]) == 2
    first, second = section["tasks"]
    note = next(v for v in first["variants"] if v["kind"] == "teade")
    story = next(v for v in second["variants"] if v["kind"] == "jutt")
    r = client.post("/api/mock/B1/kirjutamine", json={
        "seconds": 600, "answers": [], "written": "",
        "tasks": [{"id": note["id"], "text": "Tere! Ma ei saa homme tulla, sest ma olen "
                   "haige. Saame kokku laupäeval kell kuus kohvikusse."},
                  {"id": story["id"], "text": "Eile ma käisin poes."}]}).json()
    tasks = r["detail"]["tasks"]
    assert [t["id"] for t in tasks] == [note["id"], story["id"]]
    assert r["asked"] == 2 and r["correct"] == 0
    # The prompts are a model's, and the result says whose.
    assert "claude" in r["detail"]["prompts_by"].casefold()


def test_a_reading_miss_names_its_topic(client):
    section = client.get("/api/mock/B1/lugemine?seed=1").json()
    if not section["tasks"]:
        pytest.skip("no reading material in this fixture")
    r = client.post("/api/mock/B1/lugemine", json={
        "seconds": 60, "answers": [{"token": t["token"], "given": "vale"}
                                   for t in section["tasks"]]}).json()
    assert r["items"] and all(i["topic"] for i in r["items"])
    assert r["practise"] and set(r["practise"]) <= {i["topic"] for i in r["items"]}
