"""Starting a topic over.

A careless run leaves a mastery window saying "not mastered" for the next ten
questions; resetting a topic is the repair (operator action).
"""

from __future__ import annotations

from eesti import config as config_db
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


class TestEverythingMeansEverything:
    """`--everything` clears every table in the progress database — including
    checkpoints, exposure and dictation, which the readiness verdict reads — derived
    from the database, not listed.
    """

    @staticmethod
    def _tables(conn) -> dict:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for (name,) in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                    " AND name NOT LIKE 'sqlite_%'")}

    @pytest.fixture
    def furnished(self, progress):
        """A progress database with every table a real one accumulates."""
        from eesti.checkpoint import SCHEMA as CHECKPOINTS

        progress.executescript(CHECKPOINTS)
        with progress:
            progress.execute(
                "INSERT INTO checkpoints (level,asked,correct,passed,at)"
                " VALUES ('A2',12,11,1,'2026-01-01T00:00:00Z')")
        return progress

    def test_every_table_in_the_file_is_emptied(self, furnished):
        reset(furnished)
        assert set(self._tables(furnished).values()) == {0}

    def test_a_passed_checkpoint_does_not_survive_an_erase(self, furnished):
        """The one that made this more than tidiness: the verdict is gated on
        `checkpoint_passed`, so an erased learner still read as having finished
        the level."""
        from eesti.checkpoint import passed_levels

        assert passed_levels(furnished) == {"A2"}
        reset(furnished)
        assert passed_levels(furnished) == set()

    def test_it_reports_what_it_cleared(self, furnished):
        """The operator is answering a "Type ERASE" prompt. What went is worth
        printing back."""
        got = reset(furnished)
        assert "checkpoints" in got["tables_cleared"]
        assert "attempts" in got["tables_cleared"]

    def test_a_topic_reset_still_touches_only_its_two(self, furnished):
        """A topic reset leaves level-wide and per-item records (checkpoints, exposure,
        dictation) alone.
        """
        from eesti.checkpoint import passed_levels

        reset(furnished, "kusisonad")
        assert passed_levels(furnished) == {"A2"}

    def test_a_table_added_later_is_covered_without_anybody_remembering(
            self, furnished):
        """A table added later is cleared too."""
        with furnished:
            furnished.execute("CREATE TABLE IF NOT EXISTS newthing (x TEXT)")
            furnished.execute("INSERT INTO newthing VALUES ('x')")
        reset(furnished)
        assert furnished.execute("SELECT COUNT(*) FROM newthing").fetchone()[0] == 0


class TestTheEndpointRefusesTheDangerousDefault:
    def test_no_topic_and_no_flag_is_a_400(self, tmp_path, monkeypatch):
        """A missing topic is refused unless `everything` is explicit."""
        pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        monkeypatch.setattr(config_db, "PROGRESS_DB", str(tmp_path / "p.db"))
        monkeypatch.setenv("STATE_TOKEN", "tok")
        monkeypatch.delenv("PROXY_TOKEN", raising=False)
        client = TestClient(app_module.app)

        response = client.post("/api/progress/reset", json={},
                               headers={"x-state-token": "tok"})
        assert response.status_code == 400

    def test_it_needs_the_state_token(self, tmp_path, monkeypatch):
        """Reset requires `STATE_TOKEN`: an operator action, not a UI button."""
        pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        monkeypatch.setattr(config_db, "PROGRESS_DB", str(tmp_path / "p.db"))
        monkeypatch.setenv("STATE_TOKEN", "tok")
        monkeypatch.delenv("PROXY_TOKEN", raising=False)
        client = TestClient(app_module.app)

        assert client.post("/api/progress/reset",
                           json={"topic": "kusisonad"}).status_code == 403


class TestTheFabricatedAttemptsAreRepairedOnRestore:
    """The repair of fabricated placement attempts runs after a restore.

    Signature: `PROBE_ITEMS` or more attempts sharing one timestamp, all blank and
    all wrong. Idempotent by name; the `repairs` row rides the next snapshot.
    """

    @pytest.fixture
    def conn(self, tmp_path):
        return connect(tmp_path / "progress.db")

    @staticmethod
    def _burst(conn, at, n, topic="kusisonad", answer="", correct=0):
        with conn:
            conn.executemany(
                "INSERT INTO attempts (topic,item_key,correct,answer,at)"
                " VALUES (?,?,?,?,?)",
                [(topic, f"k{i}", correct, answer, at) for i in range(n)])

    @staticmethod
    def _count(conn):
        return conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]

    def test_a_fabricated_burst_goes(self, conn):
        from eesti.progress import repair_fabricated_attempts

        self._burst(conn, "2026-09-01T19:26:21+00:00", 5)
        assert repair_fabricated_attempts(conn)["removed"] == 5
        assert self._count(conn) == 0

    def test_a_real_blank_answer_is_kept(self, conn):
        """Somebody pressing Enter on one item *has* answered, wrongly. One row
        is a person; five in a second is a loop."""
        from eesti.progress import repair_fabricated_attempts

        self._burst(conn, "2026-09-01T19:26:21+00:00", 1)
        assert repair_fabricated_attempts(conn)["removed"] == 0
        assert self._count(conn) == 1

    def test_real_practice_in_the_same_second_is_kept(self, conn):
        """Answered rows are never candidates, however they are grouped."""
        from eesti.progress import repair_fabricated_attempts

        self._burst(conn, "2026-09-01T19:26:21+00:00", 5,
                    answer="mis", correct=1)
        assert repair_fabricated_attempts(conn)["removed"] == 0
        assert self._count(conn) == 5

    def test_a_slow_run_of_wrong_answers_is_kept(self, conn):
        """Blank wrong answers spread over several seconds are real, and kept."""
        from eesti.progress import repair_fabricated_attempts

        for sec in range(21, 26):
            self._burst(conn, f"2026-09-01T19:26:{sec}+00:00", 1)
        assert repair_fabricated_attempts(conn)["removed"] == 0
        assert self._count(conn) == 5

    def test_nothing_is_unrecoverable(self, conn):
        """Removed rows are saved in `repairs.detail`."""
        import json

        from eesti.progress import repair_fabricated_attempts

        self._burst(conn, "2026-09-01T19:26:21+00:00", 5)
        repair_fabricated_attempts(conn)
        detail = conn.execute("SELECT detail FROM repairs").fetchone()[0]
        rows = json.loads(detail)
        assert len(rows) == 5
        assert rows[0]["topic"] == "kusisonad"

    def test_it_runs_once_however_often_it_is_called(self, conn):
        """Every cold start restores. A repair that ran each time would delete
        a genuine burst the learner produced later."""
        from eesti.progress import repair_fabricated_attempts

        self._burst(conn, "2026-09-01T19:26:21+00:00", 5)
        assert repair_fabricated_attempts(conn)["already_applied"] is False
        again = repair_fabricated_attempts(conn)
        assert again["already_applied"] is True
        assert again["removed"] == 5

    def test_the_restore_route_applies_it(self, tmp_path, monkeypatch):
        """The whole point: no operator involved. Driven through the real
        endpoint, with a snapshot that carries the fabricated rows."""
        import base64

        from fastapi.testclient import TestClient

        from eesti import app as app_module, config

        source = connect(tmp_path / "source.db")
        self._burst(source, "2026-09-01T19:26:21+00:00", 5)
        source.commit()

        monkeypatch.setenv("STATE_TOKEN", "t")
        monkeypatch.setattr(config, "PROGRESS_DB", str(tmp_path / "live.db"))
        blob = base64.b64encode((tmp_path / "source.db").read_bytes()).decode()

        got = TestClient(app_module.app).post(
            "/api/state/import", json={"databases": {"progress": blob}},
            headers={"x-state-token": "t"}).json()
        assert got["repair"]["removed"] == 5
        assert self._count(connect(tmp_path / "live.db")) == 0
