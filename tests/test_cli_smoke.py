"""The 907 statements nothing had ever imported.

`eesti/cli.py` is the largest module in the project and sat at **0 % coverage**
— no test had ever imported it, while the app underneath it was refactored
heavily: six API routes removed, four generators unified onto a mixin, a whole
gloss layer added, `Cloze` rebuilt on `GradedItem`.

Nothing was broken, as it turns out. That is the point of writing this now
rather than after something is: a command body that calls a function which was
renamed away fails at *run* time, and until this file existed the only way to
find out was to run it by hand.

`--help` is not enough — it proves the parser and never executes the body. So
these run the commands that only read, and assert they come back clean.

Deliberately not covered here: anything that writes to a third party or needs
the network (`harvest*`, `push-content`, `notion --push`, `eval`, `models`,
`fetch-*`, `rections`, `serve`). Those are the operator's, and a test suite
that fetches ERR on every run is a test suite that hammers someone's server.
"""

from __future__ import annotations

import contextlib
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
    (["evkk"], 0),
    (["drill", "-n", "2"], 0),
    (["cloze", "-n", "2"], 0),
    (["conjugate", "-n", "2"], 0),
    (["patterns", "-n", "2"], 0),
    (["review"], 0),
]


def run(argv: list[str], stdin: str = "") -> tuple[int, str, str]:
    """Run a command with captured streams and a closed stdin.

    `drill`, `placement` and `review` are interactive loops -- they print an
    item and wait for an answer. Giving them EOF exercises the same code and
    ends the loop, which is what happens when the CLI is piped rather than
    typed at. Without it these tests hang or raise out of pytest's capture.
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
        from pathlib import Path

        source = (Path(cli.__file__)).read_text(encoding="utf-8")
        return re.findall(r'sub\.add_parser\("([a-z0-9-]+)"', source)

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
        from pathlib import Path

        source = Path(cli.__file__).read_text(encoding="utf-8")
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
    """The CLI is the only other caller of several things — which is exactly
    why `POST /api/vocab/known` went unnoticed with no caller on the page: its
    other caller was here, and here does not exist on the deployment."""

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
