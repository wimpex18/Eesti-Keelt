"""The exam as data, and the sitting the learner chose.

HARNO's own numbers (`eesti/exam.py`): four parts, 60 % to pass and no part at
zero. The sitting is learner state, so it travels in the evidence log.
"""

from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import config, evidence, exam  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)


def _progress():
    from eesti import progress

    return progress.connect(config.PROGRESS_DB)


class TestTheSpec:
    @pytest.mark.parametrize("level,total,pass_mark", [("A2", 80, 48), ("B1", 100, 60)])
    def test_the_totals_and_the_pass_mark(self, level, total, pass_mark):
        spec = exam.SPECS[level]
        assert spec.total == total and spec.pass_mark == pass_mark

    def test_every_spec_has_the_exam_s_four_parts_in_order(self):
        from eesti.readiness import PARTS

        for spec in exam.SPECS.values():
            assert [p.id for p in spec.parts] == [p[0] for p in PARTS]
            assert all(p.minutes > 0 and p.points > 0 for p in spec.parts)

    def test_speaking_says_it_cannot_be_measured_alone(self):
        """The exam is paired; the app must not imply it scores it."""
        for spec in exam.SPECS.values():
            assert "паре" in spec.part("raakimine").about

    def test_published_sittings_are_in_the_future_or_gone_from_upcoming(self):
        assert exam.upcoming(today=date(2027, 1, 1)) == []
        assert [s.level for s in exam.upcoming(today=date(2026, 1, 1))] == ["A2", "B1"]

    def test_the_api_serves_it_with_its_source(self, client):
        body = client.get("/api/exam-spec/B1").json()
        assert body["total"] == 100 and body["pass_mark"] == 60
        assert body["no_part_at_zero"] and body["source"].startswith("https://harno.ee")
        assert body["sessions"] and "2027" in body["next_year"]
        assert client.get("/api/exam-spec/C2").status_code == 404


class TestTheGoal:
    def test_none_is_chosen_to_begin_with(self, client):
        assert client.get("/api/goal").json()["goal"] is None

    def test_choosing_a_published_sitting_brings_its_registration_date(self, client):
        body = client.post("/api/goal", json={"level": "A2",
                                              "sitting": "2026-11-07"}).json()["goal"]
        assert body["registration_closes"] == "2026-10-01"
        assert client.get("/api/readiness/A2").json()["deadline"]["sitting"] == "2026-11-07"

    def test_a_level_without_a_date_is_allowed(self, client):
        """2027's dates are not published yet; the level can still be the goal."""
        body = client.post("/api/goal", json={"level": "B1"}).json()["goal"]
        assert body["level"] == "B1" and body["sitting"] is None
        assert client.get("/api/goal.ics").status_code == 404

    def test_a_bad_level_or_date_is_refused(self, client):
        assert client.post("/api/goal", json={"level": "C1"}).status_code == 400
        assert client.post("/api/goal", json={"level": "A2",
                                              "sitting": "7.11.2026"}).status_code == 400

    def test_the_goal_survives_a_replay(self, client):
        client.post("/api/goal", json={"level": "A2", "sitting": "2026-11-07"})
        with evidence.connect() as log:
            assert [e.type for e in evidence.events(log)][-1] == "goal-set"
            evidence.rebuild(log)
        assert exam.goal(_progress()).sitting == date(2026, 11, 7)

    def test_the_calendar_carries_both_dates(self, client):
        client.post("/api/goal", json={"level": "A2", "sitting": "2026-11-07"})
        ics = client.get("/api/goal.ics")
        assert ics.headers["content-type"].startswith("text/calendar")
        body = ics.text
        assert body.startswith("BEGIN:VCALENDAR") and body.rstrip().endswith("END:VCALENDAR")
        assert body.count("BEGIN:VEVENT") == 2
        assert "DTSTART;VALUE=DATE:20261007" not in body
        assert "DTSTART;VALUE=DATE:20261001" in body and "DTSTART;VALUE=DATE:20261107" in body
