"""The library: everything that is material rather than curriculum.

Step 7. The path (`curriculum.py` + `progress.py`) is ordered, gated and
pass/fail. This is the other surface, and the difference is not cosmetic.

**Keelekõdi is the case that forces the split.** Its episodes are ~30 minutes of
mixed content — some grammar, some songs, some vocabulary — with no transcript.
That is genuinely useful *exposure* and genuinely useless as a *curriculum
step*: it cannot be sequenced, gated on, or checked. Putting it on the path
would break the path's one promise, which is that finishing a step means
something.

|            | Path                  | Library            |
|------------|-----------------------|--------------------|
| ordered    | by prerequisite       | browse freely      |
| gated      | on mastery            | never              |
| measurable | pass/fail per topic   | exposure only      |

## Exposure is counted, and never called mastery

Reading a text is not passing anything, so the library records *that* an item
was opened and how long was spent, and stops there. The temptation is to turn
"37 texts read" into a percentage of something; that is exactly how progress
bars start lying. Coverage of a text's vocabulary — the number that actually
tells you whether a text is worth your time — comes from `vocab.py`, which
measures words rather than intentions.

## Licence gating is a filter, not a convention

`browse(..., public_only=True)` is what an unauthenticated request must use. It
filters on the **source's** licence rather than on anything about the item, so a
new source cannot leak by forgetting to tag its rows. ERR transcripts and HARNO
exam material live here and are owner-only; Selges keeles texts are too, pending
a licence answer. That is why Cloudflare Access is not optional.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Section:
    id: str
    et: str
    ru: str
    skills: tuple[str, ...]
    note: str


# Sections group by *what the learner does with the material*, which is not the
# same as where it came from: the ERR radio courses are Russian-language grammar
# lessons and belong with grammar, not with listening practice.
SECTIONS: tuple[Section, ...] = (
    Section("lugemine", "Lugemine", "чтение", ("lugemine",),
            "Simplified Estonian texts, sorted into relative difficulty bands."),
    Section("kuulamine", "Kuulamine", "аудирование", ("kuulamine",),
            "Audio without transcripts — exposure, not a curriculum step. Plus "
            "TTS on any text at 0.7x."),
    Section("saated", "Saated", "передачи", ("grammatika",),
            "The radio courses that do have transcripts: 28 lessons, Russian "
            "explanation with Estonian examples."),
    Section("eksam", "Eksamimaterjalid", "экзамен", ("kirjutamine", "raakimine"),
            "Official task material. Owner-only, always."),
)

_BY_ID = {s.id: s for s in SECTIONS}

SCHEMA = """
CREATE TABLE IF NOT EXISTS exposure (
    item_id  TEXT NOT NULL,
    seen_at  TEXT NOT NULL,
    minutes  REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (item_id, seen_at)
);
CREATE INDEX IF NOT EXISTS idx_exposure_item ON exposure(item_id);
"""


def by_id(section_id: str) -> Section:
    return _BY_ID[section_id]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sections(content: sqlite3.Connection, public_only: bool = False) -> list[dict]:
    """Every section with how much material is actually in it."""
    out = []
    for section in SECTIONS:
        marks = ",".join("?" * len(section.skills))
        sql = (
            f"SELECT COUNT(*), COALESCE(SUM(i.audio_url IS NOT NULL), 0)"
            f" FROM items i JOIN sources s ON s.id = i.source_id"
            f" WHERE i.skill IN ({marks})"
        )
        if public_only:
            sql += " AND s.redistributable = 1"
        total, with_audio = content.execute(sql, section.skills).fetchone()
        out.append({
            "id": section.id, "et": section.et, "ru": section.ru,
            "items": total, "with_audio": with_audio, "note": section.note,
        })
    return out


def browse(
    content: sqlite3.Connection,
    section: str,
    level: str | None = None,
    limit: int = 20,
    public_only: bool = False,
) -> list[sqlite3.Row]:
    """Material in one section. Unordered by design — this is a shelf, not a path."""
    from .sources import query

    found: list[sqlite3.Row] = []
    for skill in by_id(section).skills:
        found += query(
            content, skill=skill, level=level, public_only=public_only, limit=limit
        )
    return found[:limit]


def mark_seen(progress: sqlite3.Connection, item_id: str, minutes: float = 0.0) -> None:
    """Record that material was opened. Not a pass, and never treated as one."""
    progress.executescript(SCHEMA)
    with progress:
        progress.execute(
            "INSERT OR REPLACE INTO exposure (item_id, seen_at, minutes)"
            " VALUES (?,?,?)",
            (item_id, _now(), float(minutes)),
        )


def exposure(progress: sqlite3.Connection) -> dict:
    """Texts opened and minutes spent. Two counts, and deliberately no percentage.

    There is no denominator that would make one honest: the library grows, and
    "12 % of the library" says nothing about whether the learner can read.
    """
    progress.executescript(SCHEMA)
    rows = progress.execute(
        "SELECT COUNT(*), COUNT(DISTINCT item_id), COALESCE(SUM(minutes), 0)"
        " FROM exposure"
    ).fetchone()
    return {"openings": rows[0], "items": rows[1], "minutes": round(rows[2], 1)}


def seen_items(progress: sqlite3.Connection) -> set[str]:
    progress.executescript(SCHEMA)
    return {r[0] for r in progress.execute("SELECT DISTINCT item_id FROM exposure")}
