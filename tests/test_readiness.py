"""Should you sit the exam? An answer, and the things it refuses to claim.

- **No prediction** — no probability, no score.
- **Four parts, never one total** — ≥60 % overall and no part at zero.
- **"Cannot tell" is not "none"** — Rääkimine is paired and cannot be judged
  here; reporting it as zero practice would mislead.
"""

from __future__ import annotations

from datetime import date

import pytest

from eesti.progress import connect as progress_connect
from eesti.readiness import CONTACT, PARTS, readiness


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
def target(progress):
    """A chosen sitting, for the tests that are about the countdown itself."""
    from datetime import date as _date

    from eesti.exam import set_goal

    set_goal(progress, "A2", _date(2026, 11, 7))
    return progress


class TestTheDeadline:
    def test_no_session_is_chosen_by_default(self, progress):
        """With no sitting chosen, no countdown is shown."""
        from eesti.exam import goal

        assert goal(progress) is None

    def test_the_countdown_says_so_rather_than_going_blank(self, progress):
        result = readiness("A2", progress=progress, today=date(2026, 9, 1))
        assert result.days_to_decide is None
        assert result.countdown == "экзамен ещё не выбран"

    def test_the_deadline_block_carries_no_invented_date(self, progress):
        """A caller that renders whatever it is given would otherwise print a
        date nobody is working toward."""
        got = readiness("A2", progress=progress).to_dict()["deadline"]
        assert got["registration"] is None and got["sitting"] is None
        assert "Eksam" in got["note"]

    def test_choosing_a_sitting_brings_the_countdown_back(self, target):
        """The dates come from HARNO's published session (`exam.SESSIONS`)."""
        result = readiness("A2", progress=target, today=date(2026, 9, 1))
        assert result.days_to_decide == 30      # registration closes 2026-10-01
        assert result.days_to_sitting == 67     # sitting 2026-11-07
        assert result.countdown == "до регистрации 30 дн."

    def test_a_passed_deadline_goes_negative_rather_than_pretending(self, target):
        """Clamping at zero would quietly turn 'too late' into 'today'."""
        result = readiness("A2", progress=target, today=date(2026, 12, 1))
        assert result.days_to_decide < 0

    def test_a_published_session_closes_registration_weeks_ahead(self):
        from eesti.exam import SESSIONS

        for session in SESSIONS:
            gap = (session.sitting - session.registration_closes).days
            assert 28 <= gap <= 45, session


class TestContactThreshold:
    def test_it_is_a_contact_bar_not_a_competence_bar(self):
        """An activity count cannot support more than 'they have done this at
        least a few times', so the number stays small and honest."""
        assert 1 < CONTACT <= 5


class TestTheVerdictReadsOnlyWhatItIsGiven:
    """The verdict reads the Notion queue from the connection passed in, never a
    module-level path.
    """

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

    def test_the_contact_count_is_the_one_touched_is_decided_from(self, progress,
                                                                 tmp_path):
        """The readiness flower fills a petal segment per contact; a count that
        disagreed with `touched` would draw a full petal on an untouched part."""
        from eesti.notion import Row, connect, queue

        notion = connect(tmp_path / "n.db")
        queue(notion, Row(wrong="autot", correct="auto", why="x", tag="obj-case"))
        body = readiness("A2", progress=progress, notion=notion).to_dict()
        parts = {p["id"]: p for p in body["parts"]}
        assert body["contact_target"] == CONTACT
        assert parts["kirjutamine"]["contact"] == 1
        assert parts["kirjutamine"]["touched"] is False
        # Speaking is not counted, so it has no count rather than a zero.
        assert parts["raakimine"]["contact"] is None

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
    """Known-word counts read `vocab_status.status` (KNOWN, WELL_KNOWN), and a failed
    read reports `measured: False`, never a measured zero.
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
        """Checked against the real schema's column names."""
        cols = {r[1] for r in vocabulary.execute("PRAGMA table_info(vocab_status)")}
        assert "status" in cols
        assert "known" not in cols
