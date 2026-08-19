"""Should you sit the exam? An answer, and the things it refuses to claim.

The A2 sitting is 07.11.2026 and the decision is due 01.10.2026. That is a real
deadline with a real cost either way, which is exactly the situation in which a
confident number would be most welcome and least earned.

So the properties worth testing here are mostly refusals.

**No prediction.** Nothing in this project has seen a graded exam and there is
no population to calibrate against, so there is no probability and no score.

**Four parts, never one total.** The pass rule is ≥60% overall *and* no part at
zero. An aggregate hides the untouched part, which is the failure mode the rule
exists to punish.

**"Cannot tell" is not "none".** Rääkimine is paired and dialogic; nothing here
simulates two candidates negotiating agreement. Reporting that as zero practice
would be a claim the learner would reasonably act on.
"""

from __future__ import annotations

from datetime import date

import pytest

from eesti.progress import connect as progress_connect
from eesti.readiness import CONTACT, DECIDE_BY, PARTS, SITTING, readiness


class _Item:
    def __init__(self, topic, key):
        self.topic, self.prompt, self.answer = topic, key, "x"


@pytest.fixture
def progress(tmp_path):
    return progress_connect(tmp_path / "p.db")


class TestItRefusesToPredict:
    def test_there_is_no_score_and_no_probability(self, progress):
        body = readiness("A2", progress=progress).to_dict()
        for banned in ("score", "probability", "likelihood", "predicted"):
            assert banned not in body

    def test_the_caveat_says_so_out_loud(self, progress):
        """It travels with the verdict, not in documentation someone may skip."""
        caveat = readiness("A2", progress=progress).to_dict()["caveat"]
        # Russian: the reader is a Russian speaker learning Estonian, and a
        # caveat in the language they are still learning protects nobody.
        assert "не прогноз" in caveat


class TestAllFourParts:
    def test_every_exam_part_is_reported(self, progress):
        found = {p["id"] for p in readiness("A2", progress=progress).to_dict()["parts"]}
        assert found == {p[0] for p in PARTS}

    def test_an_untouched_part_is_named_as_the_risk(self, progress):
        """60% overall is not enough if one part is zero, so this must be the
        loudest thing the verdict says."""
        result = readiness("A2", progress=progress)
        assert any("Не тронутые" in r for r in result.reasons)

    def test_speaking_is_unknown_rather_than_zero(self, progress):
        """Nothing simulates a paired dialogue. Reporting that as 'no practice'
        would be a claim the learner would act on."""
        parts = {p.id: p for p in readiness("A2", progress=progress).parts}
        assert parts["raakimine"].touched is None
        assert parts["raakimine"].touched is not False

    def test_the_other_three_are_measurable(self, progress):
        parts = {p.id: p for p in readiness("A2", progress=progress).parts}
        for part in ("kirjutamine", "kuulamine", "lugemine"):
            assert parts[part].touched is False, part


class TestTheVerdict:
    def test_an_empty_record_is_not_ready(self, progress):
        assert readiness("A2", progress=progress).verdict == "ei ole veel"

    def test_mastery_alone_does_not_make_it_ready(self, progress):
        """Every A2 grammar topic mastered and no listening ever done is exactly
        the shape the 'no part at zero' rule fails."""
        from eesti.curriculum import TOPICS
        from eesti.progress import record

        for topic in (t for t in TOPICS if t.level == "A2" and t.generator):
            for i in range(12):
                record(progress, _Item(topic.id, f"i{i}"), correct=True)

        result = readiness("A2", progress=progress)
        assert result.verdict != "tõendid toetavad"
        assert any("Не тронутые" in r for r in result.reasons)

    def test_no_progress_database_means_unknown(self):
        """Absence of evidence is reported as such, not as a negative verdict."""
        assert readiness("A2").verdict == "teadmata"


class TestTheDeadline:
    def test_the_dates_are_the_ones_from_the_plan(self):
        assert DECIDE_BY == date(2026, 10, 1)
        assert SITTING == date(2026, 11, 7)

    def test_the_countdown_is_computed_not_guessed(self, progress):
        result = readiness("A2", progress=progress, today=date(2026, 9, 1))
        assert result.days_to_decide == 30
        assert result.days_to_sitting == 67

    def test_a_passed_deadline_goes_negative_rather_than_pretending(self, progress):
        """Clamping at zero would quietly turn 'too late' into 'today'."""
        result = readiness("A2", progress=progress, today=date(2026, 12, 1))
        assert result.days_to_decide < 0


class TestContactThreshold:
    def test_it_is_a_contact_bar_not_a_competence_bar(self):
        """An activity count cannot support more than 'they have done this at
        least a few times', so the number stays small and honest."""
        assert 1 < CONTACT <= 5


class TestTheVerdictReadsOnlyWhatItIsGiven:
    """`_parts` opened the Notion queue from `app.NOTION_DB` itself, so the
    verdict depended on a module-level path no caller could redirect. A test
    with its own fixtures still read the developer's real queue — the suite
    reported one thing locally and another in CI, and it only ever passed
    because that queue happened to be empty. Same shape as every other
    path-frozen-at-import bug in this project."""

    def test_writing_is_zero_when_no_queue_is_supplied(self, progress):
        part = {p.id: p for p in readiness("A2", progress=progress).parts}
        assert part["kirjutamine"].touched is False
        assert part["kirjutamine"].evidence.startswith("0 ")

    def test_it_counts_the_queue_it_is_handed(self, progress, tmp_path):
        from eesti.notion import Row, connect, queue

        notion = connect(tmp_path / "n.db")
        for wrong in ("raamatut", "autot", "kirjat"):
            queue(notion, Row(wrong=wrong, correct=wrong[:-1],
                              why="täissihitis", tag="obj-case"))
        part = {p.id: p for p in
                readiness("A2", progress=progress, notion=notion).parts}
        assert part["kirjutamine"].touched is True
        assert "3 " in part["kirjutamine"].evidence

    def test_queued_and_sent_are_different_facts(self, progress, tmp_path):
        """While nothing could push, the distinction did not exist and the
        evidence said "in the log" about rows that had never reached it. Only
        a sent row is somewhere the "three of a tag" rule can see it."""
        from eesti.notion import Row, connect, mark_pushed, pending, queue

        notion = connect(tmp_path / "n.db")
        for wrong in ("raamatut", "autot"):
            queue(notion, Row(wrong=wrong, correct=wrong[:-1],
                              why="täissihitis", tag="obj-case"))

        def evidence():
            return {p.id: p for p in readiness(
                "A2", progress=progress, notion=notion).parts}["kirjutamine"].evidence

        assert "ни одного" in evidence()
        mark_pushed(notion, pending(notion)[0]["id"])
        assert "1 в логе Vead" in evidence()
