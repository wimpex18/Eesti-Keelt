"""Content library: many sources, one shape, licence-aware.

The app pulls study material from very different places — public APIs, harvested
web pages, official exam PDFs, and files the user drops in by hand. They differ
in format and in something more important: **what you are allowed to do with
them.** So every row carries its `licence` and a `redistributable` flag, and
`add_items` refuses an id the ledger does not know.

**The terms themselves are in `eesti/licences.py`**, with `Source` and
`REGISTRY`, and this module re-exports both. They were 250 of this file's 672
lines and had nothing to do with the rest of it at runtime: the store never
reads a `note`, the ledger never opens a database. Why a licence is a column
rather than a README paragraph is argued there, once.

What is left here is the store: the schema, the content-hash id that makes
ingestion idempotent, and the queries the library reads.
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

# Skills map to the four exam parts, so progress can be tracked the way the exam
# scores it — 25 points each, and no part may be zero.
#
# Two are not exam parts. `grammatika` is the radio courses: Russian-language
# lessons about Estonian, which belong with grammar rather than with listening
# practice. `eksam` is material that belongs to a *level as a whole* rather than
# to one part — the annotated sample performance, the intro video, the CEFR
# descriptor, the information sheet. Forcing those into one of the four would
# have put the sample answer for writing into the writing practice list.
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
    """Whether the harvested library actually holds anything.

    Reported by `/api/health`, so "the reading list is empty" can be told apart
    from "the reading list is broken" without reading logs.

    It asks for **rows**, not for a file. The first version asked whether the
    file existed and was non-empty, which was true five minutes after deploying:
    `connect` creates the database *with its schema* on the first request, so an
    unharvested deployment reported a library it did not have.

    That is the second time this exact mistake has been made here -- the
    snapshot restore had it too, and `_has_learner_data` in `app.py` exists
    because of it. The rule both landed on: **presence of a database is not
    presence of data.**
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
    """How much material is here, and how much of it a drill can reach.

    Two numbers rather than one, because they fail separately and only one of
    them is visible. `items` is the reading library. `topic_links` is
    `topic_items`, the join `topiclinks.related()` reads and `/api/practice`
    returns as the `reading` beside every drill.

    Nothing fills `topic_items` except `cli link-topics`, run by hand: no
    harvest calls it and no deploy step does. So a freshly harvested corpus can
    be pushed with the table empty, every drill's `reading` comes back `[]`,
    and nothing anywhere says why. `deploy/push-content.sh` warns about exactly
    that -- but only at push time, and only for the operator running it. A
    deployment pushed before that warning existed, or answered with `-y`,
    cannot be asked. Now it can.

    Missing tables read as zero, like every other count here: presence of a
    database is not presence of data, and absence is not an error.
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
    """Add columns that older content databases do not have.

    The corpus is pushed to the deployment as a file, so a learner can be
    carrying a database built before a column existed. Failing to open it would
    lose the whole reading library over one `ALTER TABLE`.
    """
    have = {r[1] for r in conn.execute("PRAGMA table_info(items)")}
    if "band" not in have:
        conn.execute("ALTER TABLE items ADD COLUMN band TEXT")


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the content library, degrading to empty rather than failing.

    The harvested corpus is deliberately not in the image -- it is owner-only by
    licence -- and everything else is documented to keep working without it. On
    Cloud Run that promise broke: `EESTI_CONTENT_DB` points inside a directory
    the `VOLUME` declaration was supposed to provide, Cloud Run ignores
    `VOLUME`, and SQLite cannot create a database in a directory that is not
    there. `/api/library` and `/api/status` both returned 500 in production
    while every test passed, because every test had a writable path.

    So: make the directory if we can, and if we still cannot open the file, hand
    back an empty in-memory library. An absent corpus is a supported state; a
    500 on the status page is not.
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
    """Drop every item from one source.

    Item ids are content hashes, so improving the cleaning step changes the hash
    and `add_items` inserts alongside the old rows rather than replacing them.
    Re-harvesting is a normal operation, so it clears first.
    """
    with conn:
        cur = conn.execute("DELETE FROM items WHERE source_id = ?", (source_id,))
    return cur.rowcount


def _filters(
    skill: str | None, level: str | None, band: str | None, public_only: bool,
) -> tuple[list[str], list]:
    """The WHERE shared by `query` and `count`.

    Written once because the two must never disagree: a count computed from a
    different set of conditions than the rows it counts is a number that looks
    authoritative and is not.
    """
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
    """How many items match, ignoring any page size.

    `query` takes a `limit`, and the page printed the number of rows it got
    back as though it were the number of rows there are. Asking for 80 of 349
    reading texts produced "80 текстов" -- a page size wearing the clothes of a
    total, with no way to tell and no way to reach the other 269.

    That is the second half of a bug this file already carries the first half
    of: the comment below explains how the limit used to hide two thirds of the
    library behind one band. The ordering was fixed then; the cap was not.
    """
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

    `public_only=True` is what a public, unauthenticated request must use. It is
    a filter on the source's licence, not on anything about the item, so a new
    source cannot leak by forgetting to tag its items.
    """
    where, params = _filters(skill, level, band, public_only)
    params.append(limit)
    params.append(offset)

    # Newest-first is right for a live feed and wrong for browsing everything.
    # The harvesters write one band per run, so the newest `limit` rows are all
    # one band: with 117 raskem / 116 keskmine / 116 kergem indexed, asking
    # unfiltered for 60 returned 60 kergem, and the `kõik` option showed a list
    # identical to `kergem` while hiding two thirds of the library. The filter
    # was never wrong -- the limit reached its count before the ordering
    # reached another band.
    #
    # So when no band is asked for, rank within each band and interleave: the
    # newest of every band, then the second newest of every band, and so on.
    # Recency still orders what the learner sees inside a band, and no band can
    # be crowded out by another's harvest schedule. A specific band keeps the
    # plain newest-first ordering, because there is nothing to interleave.
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
    """Ingest material the user supplies by hand.

    Accepts a JSON array of item dicts, or a plain text/markdown file taken as a
    single passage. This is the "feed it files" path — a textbook chapter, a
    tutor's handout, a transcript typed up by hand.
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
