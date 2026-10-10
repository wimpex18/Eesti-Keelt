"""Where checked material lives: committed files, then `material.db` (ADR-0009, step 4).

A draft that passed the gates and the blind check is written to
`content/material/checked/<unit>/<slug>.json` with the pipeline's stamp in
`checks`: the gate version, the blind check's engine and batch, and the hash of
the content it vouches for. The file is committed; it is the record.

`build` puts every checked file into `data/material.db` (`config.MATERIAL_DB`)
and trusts none of them: it re-runs the deterministic gates and compares the
stamp's hash with the file's own. A file edited after its blind check, or one a
newer gate refuses, is not built. What is built:

- an `items` row with id `mat:<unit>:<slug>@<sha8>` under the public source
  `grove-material`, so the text is a library item every learner may read, with
  the label, engine and prompt version in its `meta` and no answer key;
- a `material` row with the same id holding the checked document, keys
  included, which only the server reads (`eesti/api/reports.py`).

Not into `content.db`: on the deployment that is the owner's harvested corpus,
which the Worker restores over each container and archives by the hash of its
bytes, so material built into it would vanish at a restore and writing it at
runtime would change the corpus under its archive. The material is public
repository data, so the image builds it, as it builds EKI's dictionaries into
`data/eesti.db`, and the routes and the exam tasks open it with `connect`. The
database has the library's schema, so each item is a library row as well.

A changed word is a changed hash and so a new id: an attempt recorded against
the old id keeps its question and key in the evidence log and replays as it was.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import LABEL, SOURCE_ID
from .schema import Material, dump, load

#: `content/material/`, beside the package.
ROOT = Path(__file__).resolve().parents[2] / "content" / "material"

SCHEMA = """
CREATE TABLE IF NOT EXISTS material (
    id      TEXT PRIMARY KEY,   -- mat:<unit>:<slug>@<sha8>
    unit    TEXT NOT NULL,
    slug    TEXT NOT NULL,
    kind    TEXT NOT NULL,      -- dialoog | tekst
    doc     TEXT NOT NULL,      -- the checked file, keys included: server only
    built   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_material_unit ON material(unit);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """The built material (`config.MATERIAL_DB`), empty where none is built."""
    from .. import config
    from ..sources import connect as library

    return library(path or config.MATERIAL_DB)


def checked_dir(root: Path | None = None) -> Path:
    return (root or ROOT) / "checked"


def path_for(material: Material, root: Path | None = None) -> Path:
    return checked_dir(root) / material.unit / f"{material.slug}.json"


def stamp(material: Material, *, engine: str, batch: str) -> Material:
    """The material with the pipeline's record of what it passed."""
    from . import gates

    return material.model_copy(update={"checks": {
        "gates": gates.VERSION,
        "blind": {"engine": engine, "batch": batch,
                  "on": datetime.now(timezone.utc).date().isoformat()},
        "sha8": material.sha8(),
    }})


def stamped(material: Material) -> str | None:
    """Why the stamp does not vouch for this content, or None when it does."""
    checks = material.checks or {}
    if not isinstance(checks.get("blind"), dict) or not checks["blind"].get("engine"):
        return "no blind check recorded"
    if checks.get("sha8") != material.sha8():
        return "the content changed after its checks"
    return None


def write_checked(material: Material, root: Path | None = None) -> Path:
    """Commit-ready file for a stamped material. Refuses an unstamped one: no
    key reaches `checked/` without the gates and the blind check."""
    why = stamped(material)
    if why:
        raise ValueError(f"{material.unit}/{material.slug}: {why}")
    path = path_for(material, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(material), encoding="utf-8")
    return path


def verify(material: Material, words: sqlite3.Connection | None) -> str | None:
    """Why a checked file may not be built, or None when it may."""
    from . import gates

    why = stamped(material)
    if why:
        return why
    report = gates.check(material, words)
    if report.failures:
        return "; ".join(str(f) for f in report.failures[:3])
    if report.dropped:
        # A checked file holds only items that passed; one that no longer does
        # means the gates changed under it. Re-run the pipeline, never trim here.
        return "; ".join(str(f) for f in report.dropped[:3])
    return None


def checked_files(root: Path | None = None) -> list[Path]:
    base = checked_dir(root)
    return sorted(base.glob("*/*.json")) if base.exists() else []


def build(conn: sqlite3.Connection, words: sqlite3.Connection | None,
          root: Path | None = None) -> tuple[list[str], list[tuple[Path, str]]]:
    """Replace the built material with what `checked/` holds now.

    Returns the ids built and the files refused with why. Material whose file
    is gone is removed, so `content.db` never serves what the repository dropped.
    """
    from ..sources import register

    conn.executescript(SCHEMA)
    register(conn)
    built: list[str] = []
    refused: list[tuple[Path, str]] = []
    rows = []
    for path in checked_files(root):
        try:
            material = load(path)
        except ValueError as exc:
            refused.append((path, f"does not parse: {exc}"))
            continue
        if path != path_for(material, root):
            refused.append((path, "its unit and slug do not match its path"))
            continue
        why = verify(material, words)
        if why:
            refused.append((path, why))
            continue
        rows.append(material)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute("DELETE FROM topic_items WHERE item_id IN "
                     "(SELECT id FROM items WHERE source_id = ?)", (SOURCE_ID,))
        conn.execute("DELETE FROM items WHERE source_id = ?", (SOURCE_ID,))
        conn.execute("DELETE FROM material")
        for material in rows:
            ident = material.ident()
            meta = {
                "kind": "material", "material": material.kind,
                "unit": material.unit, "slug": material.slug,
                "label": LABEL, "engine": material.authoring.engine,
                "prompt_version": material.authoring.prompt_version,
                "harno": material.harno,
                "words": len(material.body().split()),
            }
            conn.execute(
                "INSERT INTO items (id,source_id,skill,level,band,title,body,"
                "audio_url,meta,added_on) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ident, SOURCE_ID, "lugemine", None, None, material.title,
                 material.body(), None, json.dumps(meta, ensure_ascii=False),
                 now[:10]))
            conn.execute(
                "INSERT INTO material (id,unit,slug,kind,doc,built) VALUES (?,?,?,?,?,?)",
                (ident, material.unit, material.slug, material.kind,
                 json.dumps(material.model_dump(mode="json"), ensure_ascii=False), now))
            built.append(ident)
    return built, refused


def _table(conn: sqlite3.Connection) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='material'").fetchone())


def find(conn: sqlite3.Connection, ident: str) -> Material | None:
    """One built material by id, keys included."""
    if not _table(conn):
        return None
    row = conn.execute("SELECT doc FROM material WHERE id = ?", (ident,)).fetchone()
    return Material.model_validate_json(row[0]) if row else None


def for_unit(conn: sqlite3.Connection, unit_id: str) -> list[Material]:
    """The built material of one unit, dialogues first."""
    if not _table(conn):
        return []
    rows = conn.execute("SELECT doc FROM material WHERE unit = ? ORDER BY kind, slug",
                        (unit_id,)).fetchall()
    return [Material.model_validate_json(r[0]) for r in rows]
