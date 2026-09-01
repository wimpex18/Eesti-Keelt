"""Adding material by hand: `cli ingest`.

`sources.ingest_file` could do this since it was written, and nothing could
call it — no command, no route. A capability with no entry point is the same
bug as an endpoint with no caller, and this one mattered: it is the only code
that can put a textbook chapter, a tutor's handout or a typed-up transcript
into the library, and the app's whole reading side is built on material.

The licence posture is why this is more than a convenience wrapper. The project
cannot know what licence a file dropped into it carries, so the source it
defaults to is registered as **not** redistributable — the same posture it
takes towards HARNO's exam papers and ERR's transcripts. A file the learner
adds is theirs to study from and nobody's to republish.

Every test writes to its own database via `--db`, never the fixture corpus:
ingesting into a shared database would leave items behind for whatever ran
next.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys

import pytest

from eesti import cli


def run(argv: list[str]) -> tuple[int, str]:
    """Run a command with stdout captured and stdin at EOF."""
    out = io.StringIO()
    real_stdin, sys.stdin = sys.stdin, io.StringIO("")
    try:
        with contextlib.redirect_stdout(out):
            code = cli.main(argv)
    except SystemExit as exc:  # argparse exits rather than returning
        code = exc.code if exc.code is not None else 0
    finally:
        sys.stdin = real_stdin
    return (code or 0), out.getvalue()


@pytest.fixture
def library(tmp_path):
    """A database of its own, and the reader that opens it."""
    from eesti.sources import connect

    path = tmp_path / "own.db"

    def items(skill: str = "lugemine"):
        from eesti.library import browse

        return browse(connect(path), skill, limit=50)

    return path, items


class TestATextFile:
    def test_it_becomes_one_passage(self, tmp_path, library):
        path, items = library
        chapter = tmp_path / "peatukk.txt"
        chapter.write_text("Ma elan Tallinnas. Ma õpin eesti keelt.",
                           encoding="utf-8")

        code, said = run(["ingest", str(chapter), "--db", str(path)])
        assert code == 0, said
        assert "1 item" in said

        rows = items()
        assert len(rows) == 1
        assert rows[0]["body"].startswith("Ma elan Tallinnas")

    def test_the_filename_becomes_the_title(self, tmp_path, library):
        """Something has to name it on the shelf, and the learner chose the
        filename."""
        path, items = library
        chapter = tmp_path / "Tase A2 — perekond.txt"
        chapter.write_text("Meie peres on neli inimest.", encoding="utf-8")

        run(["ingest", str(chapter), "--db", str(path)])
        assert items()[0]["title"] == "Tase A2 — perekond"

    def test_the_skill_and_level_can_be_stated(self, tmp_path, library):
        path, items = library
        handout = tmp_path / "kuulamine.txt"
        handout.write_text("Kuula ja vasta.", encoding="utf-8")

        run(["ingest", str(handout), "--db", str(path),
             "--skill", "kuulamine", "--level", "A2"])
        rows = items("kuulamine")
        assert len(rows) == 1 and rows[0]["level"] == "A2"


class TestAJsonFile:
    def test_each_dict_becomes_an_item(self, tmp_path, library):
        path, items = library
        blob = tmp_path / "tekstid.json"
        blob.write_text(json.dumps([
            {"title": "Üks", "body": "Ta läks kooli."},
            {"title": "Kaks", "body": "Me sõidame bussiga."},
        ]), encoding="utf-8")

        code, said = run(["ingest", str(blob), "--db", str(path)])
        assert code == 0, said
        assert {r["title"] for r in items()} == {"Üks", "Kaks"}

    def test_broken_json_is_reported_rather_than_raised(self, tmp_path, library):
        """A file the learner typed is a file that can be malformed, and a
        traceback is not a message."""
        path, _ = library
        blob = tmp_path / "katki.json"
        blob.write_text('[{"title": "Üks",', encoding="utf-8")

        code, said = run(["ingest", str(blob), "--db", str(path)])
        assert code == 1
        assert "could not read" in said


class TestItRefusesRatherThanGuesses:
    def test_a_missing_file_says_so(self, tmp_path, library):
        path, _ = library
        code, said = run(["ingest", str(tmp_path / "ei-ole.txt"), "--db", str(path)])
        assert code == 1 and "no such file" in said

    def test_an_unregistered_source_is_refused(self, tmp_path, library):
        """The licence gate. `add_items` refuses a source that is not in the
        registry, because a row with no licence is a row nobody can reason
        about later."""
        path, _ = library
        chapter = tmp_path / "a.txt"
        chapter.write_text("Tekst.", encoding="utf-8")

        code, said = run(["ingest", str(chapter), "--db", str(path),
                          "--source", "kirjastuse-oma"])
        assert code == 1
        assert "kirjastuse-oma" in said and "licence" in said
        assert "oma-materjal" in said, "the refusal must say what to use instead"

    def test_the_refusal_does_not_blame_the_file(self, tmp_path, library):
        """`add_items` raises the right refusal with the wrong subject. Read
        through it, the learner would go looking at a file that is fine."""
        path, _ = library
        chapter = tmp_path / "a.txt"
        chapter.write_text("Tekst.", encoding="utf-8")

        _, said = run(["ingest", str(chapter), "--db", str(path),
                       "--source", "kirjastuse-oma"])
        assert "could not read" not in said

    def test_nothing_is_written_when_the_source_is_refused(self, tmp_path, library):
        path, items = library
        chapter = tmp_path / "a.txt"
        chapter.write_text("Tekst.", encoding="utf-8")

        run(["ingest", str(chapter), "--db", str(path), "--source", "puudub"])
        run(["ingest", str(chapter), "--db", str(path)])
        assert len(items()) == 1


class TestTheLicencePosture:
    def test_the_default_source_exists_and_is_not_redistributable(self):
        from eesti.sources import REGISTRY

        source = next(s for s in REGISTRY if s.id == "oma-materjal")
        assert source.redistributable is False, (
            "a file the learner supplies may be somebody's textbook; this "
            "project cannot know its licence and must not assume one")

    def test_it_says_the_licence_is_unknown(self):
        from eesti.sources import REGISTRY

        source = next(s for s in REGISTRY if s.id == "oma-materjal")
        assert "unknown" in source.licence.lower()

    def test_ingested_material_stays_out_of_anything_public(self, tmp_path, library):
        """`public_only` is how every reader asks for what may be shown
        onwards. Ingested material must never answer that."""
        from eesti.library import browse
        from eesti.sources import connect

        path, _ = library
        chapter = tmp_path / "a.txt"
        chapter.write_text("Tekst.", encoding="utf-8")
        run(["ingest", str(chapter), "--db", str(path)])

        conn = connect(path)
        assert browse(conn, "lugemine", limit=50)
        assert browse(conn, "lugemine", limit=50, public_only=True) == []


class TestItIsReachable:
    """The point of the whole change: the function had no caller."""

    def test_the_command_is_registered(self):
        import re

        from pathlib import Path

        source = Path(cli.__file__).parent.joinpath("harvest.py").read_text(
            encoding="utf-8")
        assert re.search(r'add_parser\(\s*\n?\s*"ingest"', source)

    def test_it_reaches_sources_ingest_file(self):
        import inspect

        assert "ingest_file" in inspect.getsource(cli.cmd_ingest)
