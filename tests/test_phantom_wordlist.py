"""The commands that created an empty word list by looking at one.

This is the answer to a question that stayed open across three commits. An
empty `data/eesti.db` — zero rows, complete schema — kept appearing, and the
run that tripped over it was never the run that made it: `real_wordlist` gated
on `exists()`, so the *next* run stopped skipping two curated-content tests and
checked Estonian against an empty lexicon. Two failures, in a file nobody had
touched, reading exactly like a regression.

**It was never the test suite.** Five full runs under an audit hook injected
into every subprocess (`tests/phantom/`) recorded not one read-write open of
that path. No test in the pytest process can do it — the autouse fixture in
`conftest.py` redirects `config.DB_PATH` for all of them — and the uvicorn
subprocess is ruled out by construction: `live_server` skips when the word list
is absent, which is the only condition under which the file could be created.

It was `python -m eesti.cli status`, `themes` and `vocab`, typed by a person
before `cli build`. Each called `wordlist.connect()`, which creates the file and
applies the schema, so *reading* the lexicon manufactured one. `test_cli_smoke`
runs those same commands **in-process**, where the fixture redirects the path —
which is exactly why a suite that exercises all three never showed it.

`_helpers.words_db` already existed for this, and its docstring already called
it "the fourth instance of the same bug". These three bypassed it.
"""

from __future__ import annotations

import subprocess
import sys

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

def _read_only_commands() -> list[list[str]]:
    """Every command the smoke suite calls read-only, taken from that list.

    Derived rather than written again: a second hand-maintained list beside the
    first is how this repository's most-repeated bug reproduces. It also means a
    command added there is covered here without anybody remembering to.
    """
    from test_cli_smoke import READ_ONLY

    return [argv for argv, _ in READ_ONLY]


#: The three that actually did it, kept by name so the regression is legible
#: even if the list above changes shape.
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
    """`cli serve` refuses to start without a database. That guard asked
    `exists()`, which is precisely what an empty word list satisfies — so the
    phantom defeated it and the app served every drill empty and every lookup
    missing, with no message anywhere."""

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
        """Read the source, because the whole failure was a guard that looked
        right."""
        source = (ROOT / "eesti" / "cli" / "ops.py").read_text(encoding="utf-8")
        block = source[source.index("def cmd_serve"):]
        block = block[:block.index("uvicorn.run")]
        assert "available(config.DB_PATH)" in block
        assert ".exists()" not in block


class TestTheJourneyGateCountsRowsToo:
    """Same gate, same reason, loudest consequence: an empty word list passes
    `exists()` and the whole browser suite runs against a zero-word lexicon —
    ~140 failures that look like a regression and are a missing build."""

    def test_it_asks_for_rows(self):
        source = (ROOT / "tests" / "test_e2e_journeys.py").read_text(encoding="utf-8")
        block = source[source.index("def live_server"):]
        block = block[:block.index("workdir =")]
        assert "available(words)" in block
        assert "words.exists()" not in block


class TestTheHelperThatAlreadyExisted:
    def test_words_db_refuses_rather_than_creating(self, unbuilt, capsys):
        """`_helpers.words_db` is the thing the three commands should have been
        calling all along — its docstring already called this "the fourth
        instance of the same bug"."""
        from eesti.cli._helpers import words_db

        assert words_db(unbuilt) is None
        assert not unbuilt.exists()
        assert "cli build" in capsys.readouterr().out
