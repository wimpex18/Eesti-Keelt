"""The practice rhythm and the review forecast, the two charts drawn from time.

A day's practice must land on the learner's own calendar day (Tallinn), and a
card due tomorrow must not be counted as due today.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from eesti import evidence, review
from eesti.learner import daily_activity, today_steps


def test_a_late_evening_answer_counts_on_the_tallinn_day(tmp_path):
    log = evidence.connect(tmp_path / "events.db")
    # 22:30 UTC on 1 March is 00:30 on 2 March in Tallinn (UTC+2).
    evidence._insert(log, evidence.Event(
        id="e1", type="attempt", ts="2026-03-01T22:30:00+00:00", payload={}, learner="me"))
    days = daily_activity(log, days=3, now=datetime(2026, 3, 3, 10, tzinfo=timezone.utc))
    assert [d["date"] for d in days] == ["2026-03-01", "2026-03-02", "2026-03-03"]
    assert [d["n"] for d in days] == [0, 1, 0]


def test_settings_are_not_practice(tmp_path):
    log = evidence.connect(tmp_path / "events.db")
    evidence._insert(log, evidence.Event(
        id="e2", type="reminder-settings", ts="2026-03-03T09:00:00+00:00",
        payload={}, learner="me"))
    days = daily_activity(log, days=1, now=datetime(2026, 3, 3, 10, tzinfo=timezone.utc))
    assert days[0]["n"] == 0


def test_today_steps_use_real_events_and_do_not_demand_an_empty_queue(tmp_path):
    log = evidence.connect(tmp_path / "events.db")
    for index, type_ in enumerate(("attempt", "attempt", "review", "dictation")):
        evidence._insert(log, evidence.Event(
            id=f"s{index}", type=type_, ts="2026-03-03T09:00:00+00:00",
            payload={}, learner="me",
        ))
    now = datetime(2026, 3, 3, 10, tzinfo=timezone.utc)
    steps = today_steps(log, review_due=2, now=now)
    assert steps == [
        {"id": "practice", "done": 2, "target": 5, "complete": False, "href": "#path"},
        {"id": "review", "done": 1, "target": 3, "complete": False, "href": "#review"},
        {"id": "skill", "done": 1, "target": 1, "complete": True, "href": "#read"},
    ]
    empty = today_steps(evidence.connect(tmp_path / "empty.db"), review_due=0, now=now)
    assert empty[1] == {
        "id": "review", "done": 0, "target": 0, "complete": True, "href": "#review",
    }


def test_the_forecast_puts_overdue_today_and_tomorrow_tomorrow(tmp_path):
    conn = review.connect(tmp_path / "review.db")
    now = datetime(2026, 3, 3, 10, tzinfo=timezone.utc)
    for i, due in enumerate([now - timedelta(days=2), now + timedelta(hours=3),
                             now + timedelta(hours=30)]):
        conn.execute(
            "INSERT INTO review_items (id, kind, lemma, prompt, answer, card, due)"
            " VALUES (?, 'vocab', ?, 'p', 'a', '{}', ?)", (f"c{i}", f"w{i}", due.isoformat()))
    assert review.forecast(conn, days=3, now=now) == [2, 1, 0]
