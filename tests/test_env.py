"""Loading API keys, and the two promises the module's docstring makes.

`env.py` sat at 37 % coverage with `load()` — the function that reads secrets
off disk — untested end to end. Reading it found a defect of exactly the shape
this project has already paid for once: a key that appears to be set and is
not.

A `.env` line reading `export OPENROUTER_API_KEY=sk-...`, which is what you
get from copying any shell instruction, set an environment variable literally
named `"export OPENROUTER_API_KEY"`. Nothing can read that back, so the real
key stayed unset — and `load()` announced it as loaded. The grammar chain then
ran in offline mode with the key apparently configured, which is the entry in
CLAUDE.md that begins "and a fourth".

The docstring also makes two claims that are facts about the code rather than
prose, so they are pinned here: an explicitly exported variable always wins,
and nothing in this module ever prints a key.
"""

from __future__ import annotations

import os

import pytest

from eesti import env


@pytest.fixture
def env_file(tmp_path):
    def write(text: str):
        path = tmp_path / ".env"
        path.write_text(text, encoding="utf-8")
        return path
    return write


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    """Every test gets its own environment, so none of them leaks a key."""
    for name in ("OPENROUTER_API_KEY", "GROQ_API_KEY", "NOTION_TOKEN",
                 "TESTKEY", "GOOD", "SPACED"):
        monkeypatch.delenv(name, raising=False)


class TestTheKeyThatLookedSetAndWasNot:
    def test_an_export_prefix_is_stripped(self, env_file):
        assert env.load(env_file("export OPENROUTER_API_KEY=sk-real\n")) == [
            "OPENROUTER_API_KEY"]
        assert os.environ["OPENROUTER_API_KEY"] == "sk-real"

    def test_it_no_longer_sets_a_name_nothing_can_read(self, env_file):
        env.load(env_file("export OPENROUTER_API_KEY=sk-real\n"))
        assert "export OPENROUTER_API_KEY" not in os.environ

    def test_spacing_around_the_name_survives(self, env_file):
        assert env.load(env_file("export  SPACED  = sk-2\n")) == ["SPACED"]
        assert os.environ["SPACED"] == "sk-2"

    @pytest.mark.parametrize("line", ["9INVALID=x", "BAD-NAME=y", "HAS SPACE=z",
                                      "=novalue"])
    def test_an_illegal_name_is_skipped_not_announced(self, env_file, line):
        """Skipped *and* absent from the return value. Reporting a key as
        loaded when it was not is the whole bug."""
        assert env.load(env_file(line + "\n")) == []

    def test_a_legal_name_beside_an_illegal_one_still_loads(self, env_file):
        assert env.load(env_file("BAD-NAME=y\nGOOD=z\n")) == ["GOOD"]


class TestTheDocstringsPromises:
    def test_an_exported_variable_always_wins(self, env_file, monkeypatch):
        """"this only fills in values that are not already set"."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-the-shell")
        assert env.load(env_file("OPENROUTER_API_KEY=sk-from-the-file\n")) == []
        assert os.environ["OPENROUTER_API_KEY"] == "sk-from-the-shell"

    def test_override_is_opt_in(self, env_file, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-the-shell")
        env.load(env_file("OPENROUTER_API_KEY=sk-from-the-file\n"), override=True)
        assert os.environ["OPENROUTER_API_KEY"] == "sk-from-the-file"

    def test_describe_never_returns_a_whole_secret(self, monkeypatch):
        """"Nothing here ever prints a key." That is a fact about the code, so
        it gets a test that fails when the code changes."""
        secret = "sk-or-v1-0123456789abcdefghijklmnop"
        monkeypatch.setenv("OPENROUTER_API_KEY", secret)
        for name, is_set, masked, purpose in env.describe():
            assert secret not in masked
            assert secret not in purpose
            if name == "OPENROUTER_API_KEY":
                assert is_set is True
                assert masked == "…mnop"

    def test_a_short_value_is_not_shown_at_all(self, monkeypatch):
        """Four trailing characters of a 40-character key identify it; four of
        a six-character one is most of it."""
        monkeypatch.setenv("GROQ_API_KEY", "abc123")
        masked = {n: m for n, _, m, _ in env.describe()}
        assert masked["GROQ_API_KEY"] == "set"

    def test_an_absent_key_reads_as_absent(self):
        for name, is_set, masked, _ in env.describe():
            if not is_set:
                assert masked == "—"

    def test_every_known_key_is_described(self):
        assert {n for n, _, _, _ in env.describe()} == set(env.KNOWN_KEYS)


class TestTheParser:
    def test_comments_and_blank_lines_are_ignored(self, env_file):
        assert env.load(env_file("# comment\n\n   \nGOOD=z\n")) == ["GOOD"]

    def test_a_value_containing_equals_is_kept_whole(self, env_file):
        env.load(env_file("GOOD=a=b=c\n"))
        assert os.environ["GOOD"] == "a=b=c"

    def test_quotes_are_stripped(self, env_file):
        env.load(env_file('GOOD="quoted"\n'))
        assert os.environ["GOOD"] == "quoted"
        del os.environ["GOOD"]
        env.load(env_file("GOOD='single'\n"))
        assert os.environ["GOOD"] == "single"

    def test_an_empty_value_sets_nothing(self, env_file):
        """A blank in the file must not shadow a real key from the shell."""
        assert env.load(env_file("GOOD=\n")) == []
        assert "GOOD" not in os.environ

    def test_a_missing_file_is_not_an_error(self, tmp_path):
        """Every key is optional; no .env is the normal state on a server."""
        assert env.load(tmp_path / "nothing-here") == []

    def test_a_line_with_no_equals_is_ignored(self, env_file):
        assert env.load(env_file("just some text\nGOOD=z\n")) == ["GOOD"]
