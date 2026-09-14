"""Read-only CLI commands write nothing, and "nobody answering" is not a wrong answer.

`READ_ONLY` is a promise. `_ask_terminal` raises `Stopped` on EOF and Ctrl-C
instead of returning a blank answer, which would grade as wrong and write
attempts, failed checkpoints and review items for questions nobody saw.

Checked in real subprocesses: in-process runs use `conftest`'s redirected
databases and cannot see the learner's real files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: The learner's four. Named here because the property is about these files and
#: not about `config`, which a subprocess does not inherit anyway.
LEARNER_DBS = ("progress.db", "review.db", "vocab.db", "notion.db")


def _read_only_commands() -> list[list[str]]:
    """Taken from the list whose name is the promise, not written again."""
    from test_cli_smoke import READ_ONLY

    return [argv for argv, _ in READ_ONLY]


@pytest.fixture
def learner(tmp_path, fixture_data):
    """A data directory with the fixture word list, non-empty so `placement` actually
    reaches its ask loop.
    """
    data = tmp_path / "data"
    data.mkdir()
    shutil.copy(fixture_data["words"], data / "eesti.db")
    return data


def _run(argv: list[str], data: Path, stdin: str = "") -> subprocess.CompletedProcess:
    """Run a command in a subprocess with cwd at the data directory (learner database
    paths are relative).
    """
    env = {
        **os.environ,
        "EESTI_DB": str(data / "eesti.db"),
        "EESTI_CONTENT_DB": str(data / "content.db"),
        "PYTHONPATH": str(ROOT),
    }
    return subprocess.run(
        [sys.executable, "-m", "eesti.cli", *argv],
        cwd=data.parent, env=env, input=stdin, capture_output=True, text=True)


def _snapshot(data: Path) -> dict[str, bytes | None]:
    return {name: (data / name).read_bytes() if (data / name).exists() else None
            for name in LEARNER_DBS}


class TestAReadOnlyCommandWritesNothing:
    """Every `READ_ONLY` command, as a subprocess, leaves the learner databases
    byte-identical.
    """

    @pytest.mark.parametrize("argv", _read_only_commands(),
                             ids=[" ".join(a) for a in _read_only_commands()])
    def test_the_learner_record_is_untouched(self, argv, learner):
        _run(argv, learner)          # first run may legitimately create files
        before = _snapshot(learner)
        _run(argv, learner)
        assert _snapshot(learner) == before, (
            f"`cli {' '.join(argv)}` is in READ_ONLY and changed the learner's "
            f"databases")


class TestNobodyAnsweringIsNotAWrongAnswer:
    """The one line behind all of it."""

    def test_end_of_input_stops_rather_than_answering_blank(self, monkeypatch):
        from eesti.cli._helpers import _ask_terminal
        from eesti.placement import Stopped

        def eof(_prompt=""):
            raise EOFError

        monkeypatch.setattr("builtins.input", eof)
        with pytest.raises(Stopped):
            _ask_terminal(_Item())

    def test_an_interrupt_stops_too(self, monkeypatch):
        """Ctrl-C stops a sweep."""
        from eesti.cli._helpers import _ask_terminal
        from eesti.placement import Stopped

        def interrupt(_prompt=""):
            raise KeyboardInterrupt

        monkeypatch.setattr("builtins.input", interrupt)
        with pytest.raises(Stopped):
            _ask_terminal(_Item())

    def test_a_real_blank_answer_still_gets_through(self, monkeypatch):
        """A real blank answer (Enter) is still graded as an answer."""
        from eesti.cli._helpers import _ask_terminal

        monkeypatch.setattr("builtins.input", lambda _prompt="": "")
        assert _ask_terminal(_Item()) == ""


class _Item:
    prompt = "Ma ostsin ____ (auto)."
    hint = "täissihitis"


class TestStoppingRecordsNothing:
    @pytest.fixture
    def progress(self, tmp_path):
        from eesti.progress import connect

        return connect(tmp_path / "progress.db")

    @staticmethod
    def _stop(_item):
        from eesti.placement import Stopped

        raise Stopped

    def test_a_probe_records_no_attempt(self, progress):
        from eesti.placement import Stopped, probe

        with pytest.raises(Stopped):
            probe(progress, "osastav", self._stop)
        assert progress.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0

    def test_a_sweep_ends_instead_of_marking_everything_wrong(self, progress):
        """A stopped sweep returns what it genuinely probed."""
        from eesti.placement import sweep

        assert sweep(progress, self._stop) == []
        assert progress.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0

    def test_an_abandoned_checkpoint_is_not_a_failed_one(self, progress):
        """That row feeds the readiness verdict. A sitting that never happened
        must not lower it."""
        from eesti.checkpoint import run
        from eesti.placement import Stopped

        with pytest.raises(Stopped):
            run(progress, "A1", self._stop, count=5)
        rows = progress.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
        assert rows == 0

    def test_nothing_is_queued_for_review_either(self, progress, tmp_path):
        """Missed checkpoint items go to the review queue. Items nobody saw
        would arrive there as material to re-study."""
        from eesti.checkpoint import run
        from eesti.placement import Stopped
        from eesti.review import connect, stats

        reviews = connect(tmp_path / "review.db")
        with pytest.raises(Stopped):
            run(progress, "A1", self._stop, count=5, reviews=reviews)
        assert stats(reviews)["total"] == 0
