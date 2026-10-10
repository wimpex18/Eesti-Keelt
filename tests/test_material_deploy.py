"""Checked material ships in the image, apart from the owner's corpus (ADR-0009, step 4).

`content.db` on the deployment is the owner's harvested corpus, which the
Worker restores over each container and whose bytes `corpus_revision` hashes,
so material built into it would vanish at the next restore, and writing it
there at runtime would change the corpus under its archive. The checked files
are public repository data: the image builds them into `data/material.db`, as it
builds EKI's dictionaries into `data/eesti.db`, and every reader opens that.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from test_material import material, words  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parent.parent
CHECKED = ROOT / "content" / "material" / "checked"


# ---------------------------------------------------------------------------
# The committed files
# ---------------------------------------------------------------------------

def _committed() -> list[Path]:
    return sorted(CHECKED.glob("*/*.json"))


def test_units_two_to_ten_have_a_dialogue_and_a_text():
    from eesti.units import UNITS

    kinds: dict[str, set[str]] = {}
    for path in _committed():
        doc = json.loads(path.read_text(encoding="utf-8"))
        kinds.setdefault(doc["unit"], set()).add(doc["kind"])
    wanted = {u.id for u in UNITS if 2 <= u.n <= 10}
    assert wanted <= set(kinds), sorted(wanted - set(kinds))
    assert all(kinds[u] == {"dialoog", "tekst"} for u in wanted)


@pytest.mark.parametrize("path", _committed(), ids=lambda p: f"{p.parent.name}/{p.stem}")
class TestEveryCheckedFile:
    def test_its_stamp_vouches_for_its_content(self, path):
        """Edited after its blind check, it would not be built."""
        from eesti.material import store

        m = store.load(path)
        assert path == store.path_for(m, CHECKED.parent)
        assert store.stamped(m) is None
        assert m.checks["blind"]["engine"] == "claude-haiku-5-5"

    def test_it_names_the_model_that_wrote_it(self, path):
        from eesti.material import store

        m = store.load(path)
        assert m.authoring.engine == "claude-opus-5-5"
        assert m.authoring.prompt_version.startswith("s2-draft-")

    def test_it_asks_five_questions(self, path):
        from eesti.material import store

        assert len(store.load(path).questions) == 5

    def test_a_text_has_the_endings_reading_task_4_removes(self, path):
        """`harnotasks.phrase_bank` needs four removable endings in one text."""
        from eesti.harnotasks import _removable
        from eesti.material import store
        from eesti.morph import split_sentences

        m = store.load(path)
        if m.kind != "tekst":
            pytest.skip("a dialogue is heard, not banked")
        sentences = [s for p in m.paragraphs for s in split_sentences(p)]
        assert sum(1 for s in sentences if _removable(s)) >= 4


def test_git_tracks_the_checked_files():
    """Cloud Build checks out git, so an ignored file would not reach the image."""
    import subprocess

    files = [str(p.relative_to(ROOT)) for p in _committed()]
    ignored = subprocess.run(["git", "check-ignore", "--no-index", *files], cwd=ROOT,
                             capture_output=True, text=True).stdout.split()
    assert files and not ignored


# ---------------------------------------------------------------------------
# The image
# ---------------------------------------------------------------------------

class TestTheImage:
    @pytest.fixture
    def dockerfile(self) -> str:
        return (ROOT / "Dockerfile").read_text(encoding="utf-8")

    def test_it_copies_the_checked_files(self, dockerfile):
        assert "COPY content/material/checked/ ./content/material/checked/" in dockerfile

    def test_it_builds_them_after_eki_s_levels(self, dockerfile):
        """The level gate needs EKI's list, so the build follows its import."""
        levels = dockerfile.index("eesti.cli import-levels")
        build = dockerfile.index("eesti.cli material build")
        assert levels < build

    def test_a_refusal_costs_the_material_not_the_image(self, dockerfile):
        step = re.search(r"RUN python -m eesti\.cli material build[^\n]*\n?[^\n]*", dockerfile)
        assert step and "||" in step.group(0)


# ---------------------------------------------------------------------------
# Where the build goes and where the app reads it
# ---------------------------------------------------------------------------

def _build(words, tmp_path, monkeypatch, *materials):  # noqa: F811
    """Stamp, check and build materials into a scratch `MATERIAL_DB`."""
    from eesti import config
    from eesti.material import store

    root = tmp_path / "material"
    for m in materials:
        store.write_checked(store.stamp(m, engine="claude-haiku-5-5", batch="b"), root)
    target = tmp_path / "material.db"
    monkeypatch.setattr(config, "MATERIAL_DB", target)
    with store.connect() as conn:
        ids, refused = store.build(conn, words, root)
    assert not refused
    return ids, root


def test_the_build_goes_to_material_db_by_default(words, tmp_path, monkeypatch):  # noqa: F811
    from test_material_blind import run

    from eesti import config
    from eesti.material import store

    root = tmp_path / "material"
    store.write_checked(store.stamp(material(), engine="claude-haiku-5-5", batch="b"), root)
    words_path = tmp_path / "words.db"
    words.commit()
    target = tmp_path / "built" / "material.db"
    monkeypatch.setattr(config, "MATERIAL_DB", target)
    code, out = run(["material", "build", "--root", str(root), "--words-db", str(words_path)])
    assert code == 0, out
    assert sqlite3.connect(target).execute("SELECT COUNT(*) FROM material").fetchone() == (1,)
    assert not sqlite3.connect(config.CONTENT_DB).execute(
        "SELECT name FROM sqlite_master WHERE name = 'material'").fetchone()


def test_the_unit_route_reads_material_db(words, tmp_path, monkeypatch, client):  # noqa: F811
    ids, _ = _build(words, tmp_path, monkeypatch, material())
    body = client.get("/api/material/units/kohvik").json()
    assert [m["id"] for m in body["material"]] == ids


def test_reading_task_4_is_built_from_material_db(words, tmp_path, monkeypatch):  # noqa: F811
    """With two checked texts in the image, B1 reading 4 builds without a corpus."""
    from test_harnotasks import TEXT_ONE, TEXT_TWO, _material

    from eesti import harnotasks
    from eesti.material import store

    monkeypatch.setattr(store, "verify", lambda m, w: None)   # texts outside unit 2–10 words
    _build(words, tmp_path, monkeypatch, _material("mari", TEXT_ONE),
           _material("jaan", TEXT_TWO))
    block = harnotasks.build(harnotasks.TYPES["B1-lu4"], seed=2, content=None, words=None)
    assert block is not None and len(block.questions) >= 4
