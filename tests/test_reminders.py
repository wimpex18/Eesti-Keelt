"""What is worth interrupting a day for.

A notification that arrives at the wrong time, twice, or at 3 a.m. is worse
than none: the learner turns them all off. These tests pin when each of the
four is said, and that a payload never carries anything the learner wrote.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from eesti import config, evidence, reminders, review


def at(hour: int, day: str = "2026-09-21") -> datetime:
    """A moment in Europe/Tallinn, as UTC (the app records UTC)."""
    from zoneinfo import ZoneInfo

    local = datetime.fromisoformat(f"{day}T{hour:02d}:30").replace(
        tzinfo=ZoneInfo(reminders.ZONE))
    return local.astimezone(timezone.utc)


@pytest.fixture
def log():
    with evidence.connect() as conn:
        yield conn


@pytest.fixture
def cards():
    with review.connect(config.REVIEW_DB) as conn:
        yield conn


@pytest.fixture
def progress():
    from eesti import progress as progress_module

    return progress_module.connect(config.PROGRESS_DB)


def due_cards(conn, n: int, when: datetime) -> None:
    """`n` cards already due, added the way the app adds them."""
    from eesti.review import add

    for i in range(n):
        add(conn, "obj-case", f"sõna{i}", f"küsimus {i}", "vastus", tag="obj-case")
    conn.execute("UPDATE review_items SET due = ?",
                 ((when - timedelta(days=1)).isoformat(),))
    conn.commit()


class TestTheSwitchIsOffUntilItIsOn:
    def test_nothing_is_said_before_the_learner_asks(self, log, cards, progress):
        due_cards(cards, 40, at(19))
        assert reminders.due(log, cards, progress, at(19)) == []

    def test_turning_it_on_is_learner_state(self, log):
        reminders.choose(on=True, hour=20)
        with evidence.connect() as fresh:
            assert reminders.settings(fresh)["on"] is True
            assert reminders.settings(fresh)["hour"] == 20


class TestWhenItIsSaid:
    @pytest.fixture(autouse=True)
    def _on(self):
        reminders.choose(on=True, hour=19)

    def test_a_queue_worth_a_notification(self, log, cards, progress):
        due_cards(cards, reminders.DUE_ENOUGH, at(19))
        said = reminders.due(log, cards, progress, at(19))
        assert any(r.tag.startswith("kordamine-") for r in said)

    def test_a_queue_not_worth_one(self, log, cards, progress):
        due_cards(cards, reminders.DUE_ENOUGH - 1, at(19))
        said = reminders.due(log, cards, progress, at(19))
        assert not any(r.tag.startswith("kordamine-") for r in said)

    def test_quiet_hours_are_silent_however_much_is_due(self, log, cards, progress):
        due_cards(cards, 50, at(2))
        assert reminders.due(log, cards, progress, at(2)) == []

    def test_nothing_studied_today_is_only_said_after_the_chosen_hour(
            self, log, cards, progress):
        early = [r for r in reminders.due(log, cards, progress, at(12))]
        late = [r for r in reminders.due(log, cards, progress, at(19))]
        assert not any(r.tag.startswith("plaan-") for r in early)
        assert any(r.tag.startswith("plaan-") for r in late)

    def test_a_day_that_was_studied_says_nothing_about_the_plan(
            self, log, cards, progress):
        evidence.record("exposure", {"item": "x", "skill": "lugemine"},
                        ts=at(10).isoformat())
        with evidence.connect() as fresh:
            said = reminders.due(fresh, cards, progress, at(19))
        assert not any(r.tag.startswith("plaan-") for r in said)


class TestSilenceIsMentionedOnce:
    def test_a_long_gap_is_one_reminder_not_one_a_day(self, log, cards, progress):
        reminders.choose(on=True)
        stopped = at(12, "2026-09-10")
        evidence.record("attempt", {"topic": "obj-case", "correct": 1},
                        ts=stopped.isoformat())
        tags = set()
        for day in ("2026-09-14", "2026-09-15", "2026-09-16"):
            with evidence.connect() as fresh:
                tags |= {r.tag for r in reminders.due(fresh, cards, progress,
                                                      at(19, day))
                         if r.tag.startswith("tagasi-")}
        # The tag names the day the learner stopped, so the Worker sends it once.
        assert tags == {f"tagasi-{date(2026, 9, 10)}"}


class TestTheDeadlineThatCannotBeRepeated:
    def test_registration_is_named_at_fourteen_days_and_three(self, log, cards,
                                                              progress):
        from eesti import exam

        reminders.choose(on=True)
        exam.set_goal(progress, "B1", date(2026, 11, 8))
        for days, expected in ((14, True), (13, False), (3, True)):
            when = at(19, (date(2026, 10, 1) - timedelta(days=days)).isoformat())
            said = reminders.due(log, cards, progress, when)
            assert any(r.tag.startswith("registreerimine-")
                       for r in said) is expected, days


class TestNothingPrivateTravels:
    def test_a_payload_carries_counts_and_fixed_phrases_only(self, log, cards,
                                                             progress):
        """The notification passes through Apple's or Google's service. A word
        the learner missed, a sentence they wrote, a transcript: none of it may
        be in there."""
        reminders.choose(on=True)
        evidence.record("writing", {"text": "Ma lugesin raamatut ja eksisin"})
        due_cards(cards, 30, at(19))
        with evidence.connect() as fresh:
            said = reminders.due(fresh, cards, progress, at(19))
        assert said
        for reminder in said:
            assert "raamatut" not in reminder.body
            assert "eksisin" not in reminder.body
