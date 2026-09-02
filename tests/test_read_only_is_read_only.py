"""`cli placement` wrote fifteen wrong answers into a record nobody had made.

The CLI keeps a list called `READ_ONLY`, and the name is a promise. `placement`
is on it, and running it with nothing on stdin wrote **fifteen attempts, all
marked wrong**, to the learner's own `data/progress.db`.

The cause is one line. `_helpers._ask_terminal` caught `EOFError` and
`KeyboardInterrupt` and returned `""` — and `""` is not "no answer", it is a
*wrong answer*. Every consumer of the `Ask` contract then graded and recorded
items the learner never saw:

* `cli placement </dev/null` fabricated an entire failed sweep.
* Ctrl-C could not leave a sweep, though `cmd_placement` prints "Ctrl-C to
  leave early". The interrupt became a blank answer and the sweep went on.
* `cli checkpoint` did the same, wrote a **failed checkpoint row**, and pushed
  every un-shown item into the review queue.

None of that is cosmetic. Wrong answers fill the accuracy window that gates
mastery, and the checkpoint row feeds the readiness verdict — the one deciding
A2-then-B1 against B1-alone in 2027. Practice nobody did makes the learner look
worse than they are, and `docs/status.md` names their attempt count as the one
number that matters.

**Why the existing suite could not see it.** `test_cli_smoke` runs every
`READ_ONLY` command and asserts each exits clean — but it calls `cli.main()`
*in-process*, where the autouse fixture in `conftest.py` redirects all four
learner databases. The promise the list makes was never actually tested. Same
blind spot, and the same fix, as the phantom word list: ask the property of a
real subprocess.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
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
def learner(tmp_path):
    """A learner's data directory with a real, non-empty word list.

    The word list has to be real: `placement` and `checkpoint` only reach the
    ask loop when a generator produces items, so pointing them at an empty
    lexicon would make this pass for the wrong reason — the bug would be
    invisible behind "generator produced nothing".
    """
    from eesti import config

    data = tmp_path / "data"
    data.mkdir()
    real = Path(config.ROOT) / "data" / "eesti.db"
    from eesti.wordlist import available

    if not available(real):
        pytest.skip("needs a built word list — `cli fetch-data && cli build`")
    shutil.copy(real, data / "eesti.db")
    return data


def _run(argv: list[str], data: Path, stdin: str = "") -> subprocess.CompletedProcess:
    """Run a command in a real subprocess, with cwd at the data directory.

    `config.REVIEW_DB` and friends are *relative* strings, so they resolve
    against the working directory — which is what makes cwd the whole fixture
    here, and what made the real bug reach `data/progress.db` in the repo root.
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
    """Asked of every entry in `READ_ONLY`, as a subprocess, byte for byte.

    Byte comparison rather than a row count: a command could add a row and
    delete another, or touch `topic_state` without touching `attempts`, and
    "the learner's record is unchanged" is the property, not "attempts did not
    grow".
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
        """`cmd_placement` prints "Ctrl-C to leave early". It was caught,
        turned into a blank answer, and the sweep carried on."""
        from eesti.cli._helpers import _ask_terminal
        from eesti.placement import Stopped

        def interrupt(_prompt=""):
            raise KeyboardInterrupt

        monkeypatch.setattr("builtins.input", interrupt)
        with pytest.raises(Stopped):
            _ask_terminal(_Item())

    def test_a_real_blank_answer_still_gets_through(self, monkeypatch):
        """Someone who presses Enter *has* answered, and wrongly. Collapsing
        the two is the bug; refusing both would be a different one."""
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

    def test_a_probe_records_no_attempt(self, progress, real_wordlist):
        from eesti.placement import Stopped, probe

        with pytest.raises(Stopped):
            probe(progress, "osastav", self._stop)
        assert progress.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0

    def test_a_sweep_ends_instead_of_marking_everything_wrong(
            self, progress, real_wordlist):
        """It returns what it genuinely probed — here, nothing — rather than
        walking the whole syllabus recording blanks."""
        from eesti.placement import sweep

        assert sweep(progress, self._stop) == []
        assert progress.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0

    def test_an_abandoned_checkpoint_is_not_a_failed_one(
            self, progress, real_wordlist):
        """That row feeds the readiness verdict. A sitting that never happened
        must not lower it."""
        from eesti.checkpoint import run
        from eesti.placement import Stopped

        with pytest.raises(Stopped):
            run(progress, "A1", self._stop, count=5)
        rows = progress.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
        assert rows == 0

    def test_nothing_is_queued_for_review_either(self, progress, tmp_path,
                                                 real_wordlist):
        """Missed checkpoint items go to the review queue. Items nobody saw
        would arrive there as material to re-study."""
        from eesti.checkpoint import run
        from eesti.placement import Stopped
        from eesti.review import connect, stats

        reviews = connect(tmp_path / "review.db")
        with pytest.raises(Stopped):
            run(progress, "A1", self._stop, count=5, reviews=reviews)
        assert stats(reviews)["total"] == 0


class TestTheStopIsOneClassNotTwo:
    def test_checkpoint_and_placement_agree(self):
        """Two exception classes sharing a name is how a caller catches the
        wrong one on the day it matters."""
        import eesti.checkpoint as checkpoint
        import eesti.placement as placement

        assert checkpoint.Stopped is placement.Stopped
