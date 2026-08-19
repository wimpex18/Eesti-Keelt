"""Starting a topic over.

Written because it was needed: smoke-testing the deployed app meant answering
two real questions, and those two attempts landed in the learner's own record.
Two rows out of a ten-attempt mastery window is twenty percent of the evidence
the gate is weighing — small, but not nothing, and not mine to leave there.

It earns its place beyond that. A topic answered carelessly on a phone leaves a
window saying "not mastered" for the next ten questions however well they go.
"Start this one over" is the honest repair; quietly relaxing the threshold would
not be.
"""

from __future__ import annotations

import pytest

from eesti.progress import connect, is_mastered, record, reset


class _Item:
    def __init__(self, topic, key):
        self.topic, self.prompt, self.answer = topic, key, "x"


@pytest.fixture
def progress(tmp_path):
    conn = connect(tmp_path / "progress.db")
    for i in range(4):
        record(conn, _Item("kusisonad", f"q{i}"), correct=i % 2 == 0)
    record(conn, _Item("osastav", "other"), correct=True)
    return conn


def count(conn, topic=None):
    if topic:
        return conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE topic = ?", (topic,)
        ).fetchone()[0]
    return conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]


class TestReset:
    def test_a_topic_is_cleared(self, progress):
        assert reset(progress, "kusisonad")["attempts_removed"] == 4
        assert count(progress, "kusisonad") == 0

    def test_other_topics_are_untouched(self, progress):
        """The whole point of scoping it: one bad topic is not a reason to lose
        everything else."""
        reset(progress, "kusisonad")
        assert count(progress, "osastav") == 1

    def test_the_topic_state_row_goes_too(self, progress):
        """Leaving `last_seen` behind would make a cleared topic still look
        visited, which is exactly the wrong thing to tell a resume point."""
        reset(progress, "kusisonad")
        seen = progress.execute(
            "SELECT COUNT(*) FROM topic_state WHERE topic = ?", ("kusisonad",)
        ).fetchone()[0]
        assert seen == 0

    def test_clearing_everything_is_possible_when_asked_for(self, progress):
        reset(progress)
        assert count(progress) == 0

    def test_a_cleared_topic_is_not_mastered(self, progress):
        reset(progress, "kusisonad")
        assert is_mastered(progress, "kusisonad") is False


class TestTheEndpointRefusesTheDangerousDefault:
    def test_no_topic_and_no_flag_is_a_400(self, tmp_path, monkeypatch):
        """A missing topic is far more likely to be a caller's bug than a wish
        to erase months of work."""
        pytest.importorskip("httpx", reason="TestClient needs httpx")
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
        monkeypatch.setenv("STATE_TOKEN", "tok")
        monkeypatch.delenv("PROXY_TOKEN", raising=False)
        client = TestClient(app_module.app)

        response = client.post("/api/progress/reset", json={},
                               headers={"x-state-token": "tok"})
        assert response.status_code == 400

    def test_it_needs_the_state_token(self, tmp_path, monkeypatch):
        """Destroying history must not be reachable from a page the learner has
        open — it is an operator action, not a UI button."""
        pytest.importorskip("httpx", reason="TestClient needs httpx")
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
        monkeypatch.setenv("STATE_TOKEN", "tok")
        monkeypatch.delenv("PROXY_TOKEN", raising=False)
        client = TestClient(app_module.app)

        assert client.post("/api/progress/reset",
                           json={"topic": "kusisonad"}).status_code == 403
