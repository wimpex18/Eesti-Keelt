"""Every read-only CLI command runs cleanly.

`--help` proves the parser, never the body, so these execute the commands that
only read. Excluded: anything that touches a third party or the network
(`harvest*`, `push-content`, `notion --push`, `eval`, `models`, `fetch-*`,
`rections`, `evkk`) and `serve`, which blocks.
"""

from __future__ import annotations

import contextlib
import csv
import io
import sys

import pytest

from eesti import cli

#: Every command that only reads, with arguments it actually accepts.
#: `checkpoint` is expected to *refuse* — the level is not finished in the
#: fixtures — which is a return code, not a crash, and worth keeping distinct.
READ_ONLY = [
    (["curriculum"], 0),
    (["curriculum", "--priority"], 0),
    (["curriculum", "--level", "A2"], 0),
    (["themes"], 0),
    (["vocab"], 0),
    (["status"], 0),
    (["progress"], 0),
    (["library"], 0),
    (["keys"], 0),
    (["readiness", "--level", "A2"], 0),
    (["notion"], 0),
    (["placement"], 0),
    (["drill", "-n", "2"], 0),
    (["cloze", "-n", "2"], 0),
    (["conjugate", "-n", "2"], 0),
    (["patterns", "-n", "2"], 0),
    (["review"], 0),
]


def _package_source() -> str:
    """Every module of the CLI package, concatenated (a glob, not a list)."""
    from pathlib import Path

    root = Path(cli.__file__).parent
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(root.glob("*.py")))


def test_the_source_scan_finds_the_package():
    """The guard on the guard: both checks below are regex over this text."""
    assert len(_package_source()) > 40_000


def run(argv: list[str], stdin: str = "") -> tuple[int, str, str]:
    """Run a command with captured streams and stdin at EOF, which ends interactive
    loops.
    """
    out, err = io.StringIO(), io.StringIO()
    real_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
    except SystemExit as exc:  # argparse exits rather than returning
        code = exc.code if exc.code is not None else 0
    finally:
        sys.stdin = real_stdin
    return (code or 0), out.getvalue(), err.getvalue()


class TestEveryCommandIsReachable:
    @staticmethod
    def _registered() -> list[str]:
        import re

        source = _package_source()
        return re.findall(r'sub\.add_parser\(\s*\n?\s*"([a-z0-9-]+)"', source)

    def test_there_are_commands_to_check(self):
        assert len(self._registered()) >= 25

    @pytest.mark.parametrize("name", _registered.__func__())
    def test_help_works(self, name):
        """A parser that raises on --help is a command nobody can discover."""
        code, out, err = run([name, "--help"])
        assert code == 0, err[:200]
        assert out.strip(), f"{name} --help printed nothing"

    def test_every_command_has_a_handler(self):
        """`set_defaults(func=...)` is easy to forget and fails only when run."""
        import re

        source = _package_source()
        handlers = set(re.findall(r"set_defaults\(func=(cmd_\w+)\)", source))
        missing = [h for h in handlers if not hasattr(cli, h)]
        assert not missing, f"registered but undefined: {missing}"
        assert len(handlers) >= len(self._registered()) - 1


class TestTheCommandsThatOnlyReadStillRun:
    """--help proves the parser. This proves the body."""

    @pytest.mark.parametrize(
        "argv,expected", READ_ONLY, ids=[" ".join(a) for a, _ in READ_ONLY])
    def test_it_runs_clean(self, argv, expected):
        code, out, err = run(argv)
        assert code == expected, f"{' '.join(argv)} -> {code}\n{err[:400]}"
        assert out.strip(), f"{' '.join(argv)} printed nothing at all"

    def test_build_reports_the_redirected_database_path(self, monkeypatch, tmp_path):
        """The build banner names the database path it actually builds."""
        from eesti import config

        raw = tmp_path / "raw"
        raw.mkdir()
        fields = ["word", "freq_rank", "proficiency", "pos"]
        with (raw / "est_words_160k.tsv").open(
            "w", encoding="utf-8", newline=""
        ) as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t")
            writer.writeheader()
            writer.writerow({
                "word": "raamat", "freq_rank": "200",
                "proficiency": "A1", "pos": "s",
            })
        db_path = tmp_path / "built.db"
        monkeypatch.setattr(config, "DB_PATH", db_path)
        monkeypatch.setattr(config, "RAW", raw)

        code, out, err = run(["build"])
        assert code == 0, err[:400]
        assert f"Importing word list into {db_path}" in out

    def test_a_refusal_is_a_code_not_a_crash(self):
        """`checkpoint` before the level is finished must decline and say why,
        which is a different thing from failing."""
        code, out, err = run(["checkpoint", "--level", "A1", "-n", "3"])
        assert code == 1
        assert "master" in out.lower() or "veel" in out.lower()

    def test_an_unknown_command_is_rejected(self):
        code, _, _ = run(["definitely-not-a-command"])
        assert code != 0


class TestTheCommandsUseTheSameEnginesAsTheApp:
    """Commands that are the only callers of their functions still run."""

    def test_it_does_not_reach_the_network_to_list_things(self, monkeypatch):
        import urllib.request

        def explode(*a, **k):
            raise AssertionError("a read-only command went to the network")

        monkeypatch.setattr(urllib.request, "urlopen", explode)
        for argv in (["curriculum"], ["themes"], ["library"], ["status"],
                     ["vocab"], ["progress"]):
            code, _, err = run(argv)
            assert code == 0, f"{argv}: {err[:200]}"

    def test_generated_drills_are_gradeable_without_a_network(self, monkeypatch):
        import urllib.request

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("drill generation went to the network")))
        for argv in (["drill", "-n", "3"], ["cloze", "-n", "3"],
                     ["conjugate", "-n", "3"], ["patterns", "-n", "3"]):
            code, out, _ = run(argv)
            assert code == 0 and out.strip()


class TestTheCommandsThatCannotBeRunHereStillReachTheirWork:
    """`serve` resolves its names: entered with uvicorn replaced."""

    def test_serve_reaches_uvicorn(self, monkeypatch, tmp_path):
        from eesti import config
        from eesti.cli import ops

        called = {}
        db = tmp_path / "eesti.db"
        monkeypatch.setattr(config, "DB_PATH", db)
        # A word list with a word in it; the guard refuses an empty file.
        import sqlite3

        from eesti.wordlist import SCHEMA

        conn = sqlite3.connect(db)
        conn.executescript(SCHEMA)
        conn.execute("INSERT INTO words(word) VALUES ('raamat')")
        conn.commit()
        conn.close()
        monkeypatch.setitem(
            __import__("sys").modules, "uvicorn",
            type("uvicorn", (), {"run": staticmethod(
                lambda *a, **k: called.update(app=a[0], **k))})())
        assert ops.cmd_serve(__import__("argparse").Namespace(
            host="127.0.0.1", port=8000, reload=False)) == 0
        assert called["app"] == "eesti.app:app"

    def test_serve_refuses_without_a_word_list(self, monkeypatch, tmp_path):
        """The message it prints instead, which is the branch that ran first
        and still raised."""
        from eesti import config

        monkeypatch.setattr(config, "DB_PATH", tmp_path / "missing.db")
        code, out, err = run(["serve"])
        assert code == 1 and "build" in err


class TestEveryCommandGroupIsRegistered:
    """`cli.GROUPS` is hand-ordered (`--help` order), so it is checked against the
    package's modules.
    """

    @staticmethod
    def _registrable() -> dict[str, object]:
        import importlib
        import pkgutil

        out = {}
        for info in pkgutil.iter_modules(cli.__path__):
            if info.name == "__main__":
                # Running it is its whole job; importing it is not a thing to
                # do here. It is guarded, which is why this is a skip and not
                # a process exit.
                continue
            module = importlib.import_module(f"eesti.cli.{info.name}")
            if hasattr(module, "register"):
                out[info.name] = module
        return out

    def test_there_are_groups_to_check(self):
        assert len(self._registrable()) >= 5

    def test_every_group_in_the_package_is_registered(self):
        missing = sorted(name for name, module in self._registrable().items()
                         if module not in cli.GROUPS)
        assert not missing, (
            f"{missing} define commands that `main` never adds: nothing fails, "
            f"the commands simply do not exist")

    def test_every_registered_group_is_a_module_of_the_package(self):
        known = set(self._registrable().values())
        assert all(group in known for group in cli.GROUPS)

    def test_every_command_reaches_a_handler_that_exists(self):
        """The end of the chain: each subparser's `func` must be callable, and
        `eesti.cli.cmd_x` must be the same object, since the re-export is
        derived rather than written out."""
        import argparse

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        for group in cli.GROUPS:
            group.register(sub)
        for name, sub_parser in sub.choices.items():
            func = sub_parser.get_default("func")
            assert callable(func), f"{name} has no handler"
            assert getattr(cli, func.__name__, None) is func, (
                f"eesti.cli.{func.__name__} is not the function {name} runs")


class TestImportingThePackageRunsNothing:
    """Importing `eesti/cli/__main__.py` does not run the parser."""

    def test_importing_main_module_does_not_parse_arguments(self):
        import importlib

        module = importlib.import_module("eesti.cli.__main__")
        assert module.main is cli.main
