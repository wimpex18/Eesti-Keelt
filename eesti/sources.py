"""Content library store: many sources, one shape, licence-aware.

Every row carries its source's `licence` and `redistributable` flag, and
`add_items` refuses a source id the ledger does not know. The ledger itself
(`Source`, `REGISTRY`) is in `eesti/licences.py` and re-exported here.

This module holds the schema, the content-hash id that makes ingestion
idempotent, and the queries the library reads.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Re-exported, not merely imported: `from ..sources import REGISTRY` is what
# fifteen call sites say, and moving a file is not a reason to touch fifteen
# files. `Source` comes with it because `register()` defaults to the ledger.
from .licences import REGISTRY, Source  # noqa: F401

# Skills map to the four exam parts (25 points each, none may be zero). Two are
# not parts: `grammatika` (the Russian-language radio courses) and `eksam`
# (material for a level as a whole: sample performances, intro videos,
# descriptors).
SKILLS = ("lugemine", "kuulamine", "kirjutamine", "raakimine", "grammatika",
          "eksam")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    kind            TEXT NOT NULL,   -- api | harvest | file | generated
    url             TEXT,
    licence         TEXT NOT NULL,
    redistributable INTEGER NOT NULL,
    note            TEXT
);

CREATE TABLE IF NOT EXISTS items (
    id          TEXT PRIMARY KEY,    -- content hash: ingestion is idempotent
    source_id   TEXT NOT NULL REFERENCES sources(id),
    skill       TEXT NOT NULL,
    -- CEFR, and CEFR only. NULL means nobody credible has said what level this
    -- text is, which is the honest answer for harvested prose.
    level       TEXT,                -- A1..C1, NULL if unknown
    -- Relative difficulty within its own source: kergem | keskmine | raskem.
    --
    -- A separate column because it is a separate claim. Selges keeles bands
    -- were being written into `level`, so a learner filtering "B1" got only
    -- exam material and none of the 349 reading texts -- two scales in one
    -- column, and the one anybody would filter on returned the wrong half.
    --
    -- Absolute CEFR is deliberately *not* derived for these: only 6.2% of
    -- lemmas carry a CEFR tag, and an earlier attempt rated 342 of 349
    -- deliberately-simplified news items as B2.
    band        TEXT,
    title       TEXT,
    body        TEXT,                -- transcript / passage / task text
    audio_url   TEXT,
    meta        TEXT,                -- JSON: per-source extras
    added_on    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_skill ON items(skill, level);

-- Which texts demonstrate which grammar topic, and how strongly.
--
-- Built, never hand-written: an item earns a row for a topic only if the
-- topic's own generator can cut a valid exercise out of the text. So "this
-- episode is about the completed-object contrast" is a claim the drill machinery
-- has already checked, not a label someone typed.
--
-- Precomputed rather than derived per request, because deciding it means running
-- Vabamorf over every sentence in the corpus. It lives inside content.db, so
-- pushing a harvest carries the links with it.
CREATE TABLE IF NOT EXISTS topic_items (
    topic   TEXT NOT NULL,
    item_id TEXT NOT NULL REFERENCES items(id),
    hits    INTEGER NOT NULL,
    PRIMARY KEY (topic, item_id)
);
CREATE INDEX IF NOT EXISTS idx_topic_items ON topic_items(topic, hits DESC);
CREATE INDEX IF NOT EXISTS idx_items_src   ON items(source_id);
"""


@dataclass(frozen=True)
class Item:
    source_id: str
    skill: str
    body: str = ""
    title: str = ""
    level: str | None = None
    band: str | None = None
    audio_url: str | None = None
    meta: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Content hash — re-ingesting the same material updates, never duplicates."""
        payload = f"{self.source_id}|{self.title}|{self.body}|{self.audio_url}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def available(path: Path | str) -> bool:
    """Whether the harvested library holds any rows (reported by `/api/health`).
    Asks for rows, not a file: opening creates the schema.
    """
    target = Path(path)
    if not target.exists() or target.stat().st_size == 0:
        return False
    try:
        with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as conn:
            return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] > 0
    except sqlite3.Error:
        # No `items` table, or not a database at all. Either way there is
        # nothing to read.
        return False


def corpus_counts(path: Path | str) -> dict[str, int]:
    """Corpus size (`items`) and how much a drill can reach (`topic_links`).

    `topic_items` is filled only by `cli link-topics`, so a pushed corpus can have
    texts and no links; reporting both makes that visible. Missing tables read as
    zero.
    """
    counts = {"items": 0, "topic_links": 0}
    target = Path(path)
    if not target.exists() or target.stat().st_size == 0:
        return counts
    try:
        with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as conn:
            for key, table in (("items", "items"), ("topic_links", "topic_items")):
                try:
                    counts[key] = conn.execute(
                        f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except sqlite3.Error:
                    pass
    except sqlite3.Error:
        pass
    return counts


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that older content databases lack, so a pushed older file still
    opens.
    """
    have = {r[1] for r in conn.execute("PRAGMA table_info(items)")}
    if "band" not in have:
        conn.execute("ALTER TABLE items ADD COLUMN band TEXT")


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the content library, degrading to empty rather than failing.

    The corpus is not in the image, and Cloud Run ignores `VOLUME`, so the
    directory may not exist: create it if possible, otherwise return an empty
    in-memory library.
    """
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(target)
        conn.executescript(SCHEMA)
        _migrate(conn)
    except (OSError, sqlite3.Error):
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA)
    conn.row_factory = sqlite3.Row
    return conn


def register(conn: sqlite3.Connection, sources: tuple[Source, ...] = REGISTRY) -> int:
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO sources"
            " (id,name,kind,url,licence,redistributable,note) VALUES (?,?,?,?,?,?,?)",
            [
                (s.id, s.name, s.kind, s.url, s.licence, int(s.redistributable), s.note)
                for s in sources
            ],
        )
    return len(sources)


def add_items(conn: sqlite3.Connection, items: list[Item]) -> int:
    """Insert or update by content hash. Safe to re-run on the same input."""
    known = {r["id"] for r in conn.execute("SELECT id FROM sources")}
    unknown = {i.source_id for i in items} - known
    if unknown:
        raise ValueError(
            f"unregistered source(s): {sorted(unknown)}. "
            "Add them to REGISTRY with an explicit licence first."
        )
    today = date.today().isoformat()
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO items"
            " (id,source_id,skill,level,band,title,body,audio_url,meta,added_on)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (i.id, i.source_id, i.skill, i.level, i.band, i.title, i.body,
                 i.audio_url, json.dumps(i.meta, ensure_ascii=False), today)
                for i in items
            ],
        )
    return len(items)


def clear_source(conn: sqlite3.Connection, source_id: str) -> int:
    """Drop every item from one source before re-harvesting: ids are content hashes,
    so changed cleaning would otherwise insert duplicates.
    """
    with conn:
        cur = conn.execute("DELETE FROM items WHERE source_id = ?", (source_id,))
    return cur.rowcount


def _filters(
    skill: str | None, level: str | None, band: str | None, public_only: bool,
) -> tuple[list[str], list]:
    """The WHERE shared by `query` and `count`, so they never disagree."""
    where, params = ["1=1"], []
    if skill:
        where.append("i.skill = ?")
        params.append(skill)
    if level:
        where.append("i.level = ?")
        params.append(level)
    if band:
        where.append("i.band = ?")
        params.append(band)
    if public_only:
        where.append("s.redistributable = 1")
    return where, params


def count(
    conn: sqlite3.Connection,
    skill: str | None = None,
    level: str | None = None,
    band: str | None = None,
    public_only: bool = False,
) -> int:
    """How many items match, ignoring any page size."""
    where, params = _filters(skill, level, band, public_only)
    return conn.execute(
        f"""SELECT COUNT(*) FROM items i JOIN sources s ON s.id = i.source_id
             WHERE {' AND '.join(where)}""",
        params,
    ).fetchone()[0]


def query(
    conn: sqlite3.Connection,
    skill: str | None = None,
    level: str | None = None,
    band: str | None = None,
    public_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """Fetch study items.

    `public_only=True` is what an unauthenticated request must use; it filters on
    the source's licence.
    """
    where, params = _filters(skill, level, band, public_only)
    params.append(limit)
    params.append(offset)

    # With no band filter, interleave bands (newest of each, then second newest…):
    # harvesters write one band per run, so plain newest-first would fill the limit
    # with a single band.
    if band:
        order = "ORDER BY i.added_on DESC"
        select, tail = "SELECT i.*, s.name AS source_name, s.licence, s.redistributable", ""
    else:
        select = ("SELECT i.*, s.name AS source_name, s.licence, s.redistributable,"
                  " ROW_NUMBER() OVER (PARTITION BY i.band ORDER BY i.added_on DESC)"
                  " AS _rank")
        order = "ORDER BY _rank, i.added_on DESC"
        tail = ""
    return list(
        conn.execute(
            f"""{select}
                FROM items i JOIN sources s ON s.id = i.source_id
                WHERE {' AND '.join(where)}
                {order} LIMIT ? OFFSET ?{tail}""",
            params,
        )
    )


def ingest_file(
    conn: sqlite3.Connection, path: Path, source_id: str, skill: str,
    level: str | None = None,
) -> int:
    """Ingest material the user supplies by hand: a JSON array of item dicts, or a
    text/markdown file as one passage.
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        items = [
            Item(
                source_id=source_id,
                skill=d.get("skill", skill),
                title=d.get("title", ""),
                body=d.get("body", ""),
                level=d.get("level", level),
                audio_url=d.get("audio_url"),
                meta=d.get("meta", {}),
            )
            for d in json.loads(raw)
        ]
    else:
        items = [Item(source_id, skill, body=raw, title=path.stem, level=level)]
    return add_items(conn, items)
