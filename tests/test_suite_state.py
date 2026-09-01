"""What the suite says about the conditions it ran under.

`data/` is git-ignored, so the same command runs materially different suites on
two machines and prints "passed" on both: a built word list unlocks tests a
fresh checkout skips, a harvested corpus unlocks more, and without Playwright
the browser journeys vanish entirely.

That is not a bug to fix — those inputs are large, licensed, or slow, and
skipping is the right answer. What was wrong is that the *result did not say
so*. It cost a real mistake: a browser run reported "144 skipped" after the
dataset had been deleted, and the comparison it was being used for measured
nothing at all. A skip is a fine answer; a skip nobody can see is not.

So the run states its own conditions, in the header and again in the summary,
because `-q` — the command every document here names — hides the header.
"""

from __future__ import annotations

import pytest

from conftest import describe_dataset


class TestItDescribesWhatIsPresent:
    def test_a_full_machine_names_its_numbers(self):
        said = describe_dataset({"words": 160316, "corpus": 349,
                                 "browsers": ["chromium", "webkit"]})
        assert "160,316 words" in said
        assert "349 items" in said
        assert "chromium, webkit" in said

    def test_it_never_prints_a_bare_zero(self):
        """`0 words` reads as a number that was measured. `absent` reads as a
        thing that is missing, which is what it is."""
        said = describe_dataset({"words": 0, "corpus": 0, "browsers": []})
        assert "0 words" not in said and "0 items" not in said
        assert said.count("absent") == 2


class TestItSaysWhatToRun:
    """A line that reports a gap without naming the fix makes the reader go
    looking. Every branch here names the command."""

    def test_a_missing_word_list_names_the_build(self):
        said = describe_dataset({"words": 0, "corpus": 12, "browsers": []})
        assert "cli fetch-data && cli build" in said

    def test_a_missing_corpus_names_the_harvest(self):
        said = describe_dataset({"words": 5, "corpus": 0, "browsers": []})
        assert "cli harvest-reading" in said

    def test_no_browser_says_the_journeys_skip_entirely(self):
        said = describe_dataset({"words": 5, "corpus": 5, "browsers": []})
        assert "skips entirely" in said


class TestReadingTheStateCannotBreakARun:
    """This runs before every session, including on machines where none of it
    exists. A header that raises takes the whole suite with it."""

    def test_it_survives_everything_being_absent(self, monkeypatch, tmp_path):
        from eesti import config
        from conftest import dataset_state

        monkeypatch.setattr(config, "DB_PATH", tmp_path / "nothing.db")
        monkeypatch.setattr(config, "CONTENT_DB", tmp_path / "nothing-either.db")
        state = dataset_state()
        assert state["words"] == 0 and state["corpus"] == 0
        assert describe_dataset(state)

    def test_it_does_not_create_the_databases_it_looks_for(self, monkeypatch, tmp_path):
        """Presence of a database is not presence of data — and opening one to
        find out would *create* it, which is this project's oldest bug. Twice
        it made an empty deployment look full."""
        from eesti import config
        from conftest import dataset_state

        missing = tmp_path / "must-not-appear.db"
        monkeypatch.setattr(config, "DB_PATH", missing)
        monkeypatch.setattr(config, "CONTENT_DB", tmp_path / "nor-this.db")
        dataset_state()
        assert not missing.exists(), "reading the state created a database"

    def test_a_broken_read_is_not_fatal(self, monkeypatch):
        from conftest import dataset_state

        def explode(*args, **kwargs):
            raise RuntimeError("disk on fire")

        monkeypatch.setattr("eesti.wordlist.available", explode)
        assert dataset_state()["words"] == 0


class TestTheEnginesAreReportedOnce:
    """Against the directory scan directly, not through `dataset_state`.

    The first version of this test went through `dataset_state`, which reports
    no browsers at all unless the `playwright` package is importable. It passed
    here and failed in CI, where playwright is not installed — a test whose
    result depended on undeclared local state, in the one file whose subject is
    tests whose results depend on undeclared local state.
    """

    def test_one_directory_per_engine_is_not_three_browsers(self, tmp_path):
        """Playwright unpacks `chromium-1194` and `chromium_headless_shell-1194`
        beside each other. They are one engine."""
        from conftest import installed_engines

        for name in ("chromium-1194", "chromium_headless_shell-1194", "webkit-2336"):
            (tmp_path / name).mkdir()
        assert installed_engines(tmp_path) == ["chromium", "webkit"]

    def test_an_empty_directory_is_no_engines(self, tmp_path):
        from conftest import installed_engines

        assert installed_engines(tmp_path) == []

    def test_a_directory_that_is_not_there_is_not_an_error(self, tmp_path):
        """It runs on every machine, including ones that have never had a
        browser."""
        from conftest import installed_engines

        assert installed_engines(tmp_path / "never-existed") == []


class TestAnEmptyWordListIsNotAWordList:
    """The fixture that gates on the real lexicon asks whether it holds words.

    It asked `exists()`, which is this project's oldest bug written into the
    fixture meant to avoid it: a full run leaves an empty `data/eesti.db`
    behind, and on the next run two curated-content tests stopped skipping and
    checked Estonian against an empty lexicon. They failed, in a file nothing
    had touched, looking exactly like a regression.
    """

    @staticmethod
    def _empty_wordlist(path):
        import sqlite3

        conn = sqlite3.connect(path)
        conn.executescript(
            "CREATE TABLE words(word TEXT); CREATE TABLE object_cases(word TEXT);")
        conn.close()
        return path

    def test_a_phantom_database_does_not_count_as_built(self, tmp_path):
        from eesti.wordlist import available

        assert not available(self._empty_wordlist(tmp_path / "eesti.db"))

    def test_neither_does_a_missing_one(self, tmp_path):
        from eesti.wordlist import available

        assert not available(tmp_path / "never-built.db")

    def test_the_fixture_gates_on_that_and_not_on_the_file(self):
        """Read from the source, because the whole failure was a fixture that
        looked right."""
        import inspect

        from pathlib import Path

        source = Path(__file__).with_name("conftest.py").read_text(encoding="utf-8")
        block = source[source.index("def real_wordlist"):]
        block = block[:block.index("\n\n\n")]
        assert "available(real)" in block, "the fixture is back to asking exists()"
        assert "if not real.exists()" not in block


class TestTheRunSaysWhenItCreatesAPhantom:
    """The empty `data/eesti.db` a full run leaves behind.

    Making `real_wordlist` count rows fixed the *failure* — two curated-content
    tests no longer check Estonian against an empty lexicon. It did not fix the
    file, and it did not answer who writes it. That stayed open because the
    evidence arrives one run late and in the wrong place: run one creates it
    silently, run two fails somewhere unrelated.

    So the run reports it, in the run that did it. Not a fix for the writer —
    a fix for the *silence*, which is what made the writer hard to find.
    """

    class _Reporter:
        def __init__(self):
            self.lines: list[str] = []

        def write_line(self, line, **kw):
            self.lines.append(line)

    @staticmethod
    def _empty(path):
        import sqlite3

        conn = sqlite3.connect(path)
        conn.executescript(
            "CREATE TABLE words(word TEXT); CREATE TABLE object_cases(word TEXT);")
        conn.close()
        return path

    def test_it_says_so_when_one_appears(self, monkeypatch, tmp_path):
        import conftest
        from eesti import config

        target = self._empty(tmp_path / "eesti.db")
        monkeypatch.setattr(config, "DB_PATH", target)
        monkeypatch.setitem(conftest._PHANTOM, "existed", False)
        reporter = self._Reporter()
        conftest._report_the_phantom(reporter)
        assert any("EMPTY" in line for line in reporter.lines)

    def test_it_says_nothing_when_the_word_list_was_already_there(
            self, monkeypatch, tmp_path):
        """The normal case on a built machine. A guard that shouts every run is
        a guard people learn to scroll past."""
        import conftest
        from eesti import config

        monkeypatch.setattr(config, "DB_PATH", self._empty(tmp_path / "eesti.db"))
        monkeypatch.setitem(conftest._PHANTOM, "existed", True)
        reporter = self._Reporter()
        conftest._report_the_phantom(reporter)
        assert reporter.lines == []

    def test_a_word_list_built_during_the_run_is_not_a_phantom(
            self, monkeypatch, tmp_path):
        """`cli build` in a test creates the file legitimately. The difference
        is rows, which is this project's oldest rule and the same question
        `available()` asks."""
        import sqlite3

        import conftest
        from eesti import config

        target = self._empty(tmp_path / "eesti.db")
        conn = sqlite3.connect(target)
        conn.execute("INSERT INTO words VALUES ('raamat')")
        conn.commit()
        conn.close()
        monkeypatch.setattr(config, "DB_PATH", target)
        monkeypatch.setitem(conftest._PHANTOM, "existed", False)
        reporter = self._Reporter()
        conftest._report_the_phantom(reporter)
        assert reporter.lines == []

    def test_it_names_the_caller_when_the_call_was_in_process(
            self, monkeypatch, tmp_path):
        import conftest
        from eesti import config

        monkeypatch.setattr(config, "DB_PATH", self._empty(tmp_path / "eesti.db"))
        monkeypatch.setitem(conftest._PHANTOM, "existed", False)
        monkeypatch.setitem(conftest._PHANTOM, "stack", "  File \"culprit.py\"\n")
        reporter = self._Reporter()
        conftest._report_the_phantom(reporter)
        assert any("culprit.py" in line for line in reporter.lines)

    def test_a_subprocess_is_reported_as_a_subprocess(self, monkeypatch, tmp_path):
        """The in-process spy that came before this never caught the writer,
        and the reason is the answer: a patched attribute in this interpreter
        is invisible in another one. Saying "no stack" is the finding, not a
        gap in the report."""
        import conftest
        from eesti import config

        monkeypatch.setattr(config, "DB_PATH", self._empty(tmp_path / "eesti.db"))
        monkeypatch.setitem(conftest._PHANTOM, "existed", False)
        monkeypatch.setitem(conftest._PHANTOM, "stack", None)
        reporter = self._Reporter()
        conftest._report_the_phantom(reporter)
        assert any("subprocess" in line for line in reporter.lines)


class TestTheWatcherIsArmedWhereEveryRunReachesIt:
    def test_it_is_armed_at_session_start(self):
        """It was armed from `pytest_report_header`, which pytest does not call
        under `-q` — the command every document here names. The guard was off
        in exactly the runs it was written for, which is the mistake the header
        itself exists to prevent, made one function further down.
        """
        import inspect

        import conftest

        assert "_watch_for_the_phantom" in inspect.getsource(
            conftest.pytest_sessionstart)

    def test_a_read_only_open_is_not_a_creation(self, monkeypatch, tmp_path):
        """`wordlist.available` opens `mode=ro` to answer whether the file is
        there. Counting that as the creation reports the checker as the
        culprit."""
        import conftest
        from eesti import config

        target = tmp_path / "eesti.db"
        monkeypatch.setattr(config, "DB_PATH", target)
        monkeypatch.setitem(conftest._PHANTOM, "stack", None)
        monkeypatch.setitem(conftest._PHANTOM, "existed", None)
        conftest._watch_for_the_phantom()
        from eesti.wordlist import available

        available(target)
        assert conftest._PHANTOM["stack"] is None
