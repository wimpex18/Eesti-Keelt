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
from eesti.readiness import CONTACT, EXAMPLE_TARGET, PARTS, readiness


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
        assert readiness("A2", progress=progress).verdict == "ещё нет"

    def test_mastery_alone_does_not_make_it_ready(self, progress):
        """Every A2 grammar topic mastered and no listening ever done is exactly
        the shape the 'no part at zero' rule fails."""
        from eesti.curriculum import TOPICS
        from eesti.progress import record

        for topic in (t for t in TOPICS if t.level == "A2" and t.generator):
            for i in range(12):
                record(progress, _Item(topic.id, f"i{i}"), correct=True)

        result = readiness("A2", progress=progress)
        assert result.verdict != "данные говорят «да»"
        assert any("Не тронутые" in r for r in result.reasons)

    def test_no_progress_database_means_unknown(self):
        """Absence of evidence is reported as such, not as a negative verdict."""
        assert readiness("A2").verdict == "неизвестно"


@pytest.fixture
def target(monkeypatch):
    """A chosen sitting, for the tests that are about the countdown itself."""
    from eesti import readiness as module

    monkeypatch.setattr(module, "TARGET", EXAMPLE_TARGET)


class TestTheDeadline:
    def test_no_session_is_chosen_by_default(self):
        """The November 2026 A2 rehearsal was declined on 2026-08-20 in favour
        of another year's study. Counting down to it after that is not
        motivation, it is a reproach for a decision already made."""
        from eesti import readiness as module

        assert module.TARGET is None

    def test_the_countdown_says_so_rather_than_going_blank(self, progress):
        result = readiness("A2", progress=progress, today=date(2026, 9, 1))
        assert result.days_to_decide is None
        assert result.countdown == "экзамен ещё не выбран"

    def test_the_deadline_block_carries_no_invented_date(self, progress):
        """A caller that renders whatever it is given would otherwise print a
        date nobody is working toward."""
        got = readiness("A2", progress=progress).to_dict()["deadline"]
        assert got["registration"] is None and got["sitting"] is None
        assert "2027" in got["note"]

    def test_setting_a_target_brings_the_countdown_back(self, progress, target):
        result = readiness("A2", progress=progress, today=date(2026, 9, 1))
        assert result.days_to_decide == 30
        assert result.days_to_sitting == 67
        assert result.countdown == "до регистрации 30 дн."

    def test_a_passed_deadline_goes_negative_rather_than_pretending(
        self, progress, target
    ):
        """Clamping at zero would quietly turn 'too late' into 'today'."""
        result = readiness("A2", progress=progress, today=date(2026, 12, 1))
        assert result.days_to_decide < 0

    def test_the_example_keeps_the_calendar_shape(self):
        """Kept so choosing a 2027 session is copying a shape rather than
        re-reading HARNO's calendar: registration closes about five weeks
        before the sitting."""
        decide, sitting = EXAMPLE_TARGET
        assert 28 <= (sitting - decide).days <= 45


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


class TestTheVocabularyLineCountedNothing:
    """It read zero for every learner, always, and said it had measured.

    `_vocabulary` asked `WHERE known = 1`. `vocab_status` has no `known`
    column — it is `status`, on the ladder
    `UNKNOWN, LEARNING, KNOWN, IGNORED, WELL_KNOWN = 0, 1, 5, 98, 99`. Every
    call raised `OperationalError`, a bare `except sqlite3.Error` turned it
    into `0`, and the screen told a learner who had marked hundreds of words
    **"0 из 997 слов уровня"**.

    Two faults, and the second is the worse one. A wrong column name is a typo.
    Reporting the failure as a *measurement of zero* — `measured: True`, which
    is what the page gates the line on — is what kept it invisible.
    """

    @pytest.fixture
    def vocabulary(self, tmp_path):
        from eesti.vocab import connect

        return connect(tmp_path / "vocab.db")

    @pytest.fixture
    def words(self, tmp_path):
        """A tiny word list with a known level split."""
        import sqlite3

        path = tmp_path / "words.db"
        conn = sqlite3.connect(path)
        conn.executescript(
            "CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INTEGER,"
            " proficiency TEXT, pos TEXT);")
        conn.executemany(
            "INSERT INTO words VALUES (?,1,?,'S')",
            [("raamat", "A2"), ("koer", "A2"), ("maja", "A2"),
             ("teadus", "B1"), ("uurimus", "B1")])
        conn.commit()
        return conn

    def test_a_word_marked_known_is_counted(self, vocabulary, words):
        from eesti.readiness import _vocabulary
        from eesti.vocab import KNOWN, set_status

        set_status(vocabulary, "raamat", KNOWN)
        assert _vocabulary(vocabulary, words, "A2")["known"] == 1

    def test_it_is_scoped_to_the_level_it_names(self, vocabulary, words):
        """The line reads "N из M слов уровня". Counting every known word at
        any level against one level's total can exceed 100 %, and means
        nothing when it does."""
        from eesti.readiness import _vocabulary
        from eesti.vocab import KNOWN, set_status

        for lemma in ("raamat", "koer", "teadus", "uurimus"):
            set_status(vocabulary, lemma, KNOWN)
        assert _vocabulary(vocabulary, words, "A2")["known"] == 2
        assert _vocabulary(vocabulary, words, "B1")["known"] == 2

    def test_a_word_the_learner_skipped_is_not_known(self, vocabulary, words):
        """`IGNORED` is "ei ole minu jaoks". Counting it would inflate the
        number with exactly the words they chose not to spend time on."""
        from eesti.readiness import _vocabulary
        from eesti.vocab import IGNORED, KNOWN, set_status

        set_status(vocabulary, "raamat", KNOWN)
        set_status(vocabulary, "koer", IGNORED)
        assert _vocabulary(vocabulary, words, "A2")["known"] == 1

    def test_merely_meeting_a_word_is_not_knowing_it(self, vocabulary, words):
        """`difficulty` counts `status >= 1` because comprehensibility is about
        exposure. The verdict is not: `LEARNING` is a word in progress."""
        from eesti.readiness import _vocabulary
        from eesti.vocab import LEARNING, set_status

        set_status(vocabulary, "raamat", LEARNING)
        assert _vocabulary(vocabulary, words, "A2")["known"] == 0

    def test_an_unreadable_vocabulary_is_unmeasured_not_zero(self, words, tmp_path):
        """The fault that hid the other one. An unmeasurable part is reported
        as unmeasured everywhere else in this file; a zero here is a claim
        about the learner rather than about the read."""
        import sqlite3

        from eesti.readiness import _vocabulary

        empty = sqlite3.connect(tmp_path / "no-schema.db")   # no vocab_status
        got = _vocabulary(empty, words, "A2")
        assert got["measured"] is False

    def test_a_real_count_still_says_it_measured(self, vocabulary, words):
        from eesti.readiness import _vocabulary

        assert _vocabulary(vocabulary, words, "A2")["measured"] is True

    def test_the_query_names_a_column_that_exists(self, vocabulary):
        """Read from the schema, because the whole bug was a column name that
        looked plausible and was not there."""
        cols = {r[1] for r in vocabulary.execute("PRAGMA table_info(vocab_status)")}
        assert "status" in cols
        assert "known" not in cols
