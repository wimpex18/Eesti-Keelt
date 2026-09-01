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
    def test_one_directory_per_engine_is_not_three_browsers(self, monkeypatch, tmp_path):
        """Playwright unpacks `chromium-1194` and `chromium_headless_shell-1194`
        beside each other. They are one engine."""
        from conftest import dataset_state

        for name in ("chromium-1194", "chromium_headless_shell-1194", "webkit-2336"):
            (tmp_path / name).mkdir()
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
        assert dataset_state()["browsers"] == ["chromium", "webkit"]
