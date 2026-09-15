"""Reading the word list never creates one.

`wordlist.connect()` creates the file and schema, so a read-only command run
before `cli build` would leave an empty `data/eesti.db` that later looks like a
built lexicon. Read-only commands go through `_helpers.words_db`, which checks
`available()` first. Checked in subprocesses: in-process runs use `conftest`'s
redirected paths.
"""

from __future__ import annotations

import subprocess
import sys

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

def _read_only_commands() -> list[list[str]]:
    """Every read-only command, taken from `test_cli_smoke.READ_ONLY`."""
    from test_cli_smoke import READ_ONLY

    return [argv for argv, _ in READ_ONLY]


#: The commands that once created it, named so a regression is legible.
CONFIRMED_CREATORS = ["status", "themes", "vocab"]


@pytest.fixture
def unbuilt(tmp_path, monkeypatch):
    """A repo whose word list has not been built, without touching the real one."""
    data = tmp_path / "data"
    data.mkdir()
    return data / "eesti.db"


def _run(argv: list[str], db: Path) -> subprocess.CompletedProcess:
    import os

    env = {
        **os.environ,
        "EESTI_DB": str(db),
        "EESTI_CONTENT_DB": str(db.parent / "content.db"),
        "PYTHONPATH": str(ROOT),
    }
    return subprocess.run([sys.executable, "-m", "eesti.cli", *argv],
                          cwd=ROOT, env=env, capture_output=True, text=True)


class TestReadingTheLexiconDoesNotCreateOne:
    """The property, asked of every read-only command rather than the three
    that happened to be caught. A source grep cannot express this: `cli build`
    and `cli export` open the word list to *write* it and must keep creating."""

    @pytest.mark.parametrize("argv", _read_only_commands(),
                             ids=[" ".join(a) for a in _read_only_commands()])
    def test_the_file_is_not_invented(self, argv, unbuilt):
        _run(argv, unbuilt)
        assert not unbuilt.exists(), (
            f"`cli {' '.join(argv)}` created {unbuilt.name} just by reading it "
            f"— the next run will treat that as a built word list")

    @pytest.mark.parametrize("command", CONFIRMED_CREATORS)
    def test_it_says_what_to_run(self, command, unbuilt):
        """Refusing silently would trade one confusing failure for another."""
        done = _run([command], unbuilt)
        assert "cli build" in done.stdout + done.stderr

    @pytest.mark.parametrize("command", CONFIRMED_CREATORS)
    def test_it_does_not_crash(self, command, unbuilt):
        """A missing build is an ordinary state, not an error condition."""
        done = _run([command], unbuilt)
        assert "Traceback" not in done.stderr, done.stderr[-600:]


class TestTheServeGuardCountsRows:
    """`cli serve` refuses an empty word list (rows, not `exists()`)."""

    def test_an_empty_word_list_is_still_no_database(self, unbuilt):
        import sqlite3

        from eesti.wordlist import SCHEMA

        conn = sqlite3.connect(unbuilt)
        conn.executescript(SCHEMA)
        conn.close()
        assert unbuilt.exists(), "the phantom is a real file; that was the trap"

        done = _run(["serve"], unbuilt)
        assert done.returncode == 1
        assert "No database yet" in done.stderr

    def test_the_guard_reads_from_the_source(self):
        """The guard reads `available`, checked in its source."""
        source = (ROOT / "eesti" / "cli" / "ops.py").read_text(encoding="utf-8")
        block = source[source.index("def cmd_serve"):]
        block = block[:block.index("uvicorn.run")]
        assert "available(config.DB_PATH)" in block
        assert ".exists()" not in block


class TestTheJourneyGateCountsRowsToo:
    """The browser-suite gate counts rows too."""

    def test_it_asks_for_rows(self):
        source = (ROOT / "tests" / "test_e2e_journeys.py").read_text(encoding="utf-8")
        block = source[source.index("def live_server"):]
        block = block[:block.index("workdir =")]
        assert "available(words)" in block
        assert "words.exists()" not in block


class TestTheHelperThatAlreadyExisted:
    def test_words_db_refuses_rather_than_creating(self, unbuilt, capsys):
        """`_helpers.words_db` refuses rather than creating a word list."""
        from eesti.cli._helpers import words_db

        assert words_db(unbuilt) is None
        assert not unbuilt.exists()
        assert "cli build" in capsys.readouterr().out
