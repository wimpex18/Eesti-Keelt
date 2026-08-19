"""Content library: many sources, one shape, licence-aware.

The app pulls study material from very different places — public APIs, harvested
web pages, official exam PDFs, and files the user drops in by hand. They differ
in format and in something more important: **what you are allowed to do with
them.**

That is why `licence` and `redistributable` are first-class columns rather than a
note in a README. Once the app is on a public URL, "can this be served to an
anonymous visitor?" is a question every single item must be able to answer, and a
flag on the row is the only way to answer it reliably.

    redistributable = 1  ->  may be served publicly (CC-BY, CC-BY-SA, public API)
    redistributable = 0  ->  owner only, behind auth (HARNO exam material,
                             copyrighted transcripts, anything hand-fed)

HARNO material is the case that forces this. Downloading the official exam PDFs
and MP3s to study from is ordinary personal use. Serving them from a public URL
is redistribution of a state agency's copyrighted work. The same file is fine in
one place and not the other, so access control has to be data-driven — and it
means Cloudflare Access is not a nice-to-have but the thing that keeps this
legitimate.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Skills map to the four exam parts, so progress can be tracked the way the exam
# scores it — 25 points each, and no part may be zero.
SKILLS = ("lugemine", "kuulamine", "kirjutamine", "raakimine", "grammatika")

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
    level       TEXT,                -- A1..C1, NULL if unknown
    title       TEXT,
    body        TEXT,                -- transcript / passage / task text
    audio_url   TEXT,
    meta        TEXT,                -- JSON: per-source extras
    added_on    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_skill ON items(skill, level);
CREATE INDEX IF NOT EXISTS idx_items_src   ON items(source_id);
"""


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    kind: str
    licence: str
    redistributable: bool
    url: str | None = None
    note: str = ""


@dataclass(frozen=True)
class Item:
    source_id: str
    skill: str
    body: str = ""
    title: str = ""
    level: str | None = None
    audio_url: str | None = None
    meta: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Content hash — re-ingesting the same material updates, never duplicates."""
        payload = f"{self.source_id}|{self.title}|{self.body}|{self.audio_url}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


# The registry. Every source this app is allowed to touch, with the licence that
# governs it. Adding a source means making a licence decision, deliberately.
REGISTRY: tuple[Source, ...] = (
    Source(
        "err-r4", "ERR Raadio 4 keeleõppesaated", "harvest",
        "© ERR — personal study only", False,
        "https://r4.err.ee/arhiiv/kak_eto_po_estonski",
        "~170 episodes across 3 archives, transcript + audio. Archives are "
        "closed and static, so harvest once and never re-fetch.",
    ),
    Source(
        "err-lihtsad", "ERR Lihtsad uudised", "harvest",
        "© ERR — personal study only", False,
        "https://news.err.ee/k/lihtsad-uudised",
        "Simplified Estonian news for learners, audio + text. Weekly, ongoing.",
    ),
    Source(
        "harno", "HARNO tasemeeksami materjalid", "file",
        "© Haridus- ja Noorteamet — personal study only", False,
        "https://harno.ee/eesti-keele-tasemeeksamid",
        "Official sample tasks and listening MP3s for A2/B1/B2/C1. Free to "
        "download and study from; NOT free to republish. Owner-only, always.",
    ),
    Source(
        "eis", "EIS avalikud ülesanded", "api",
        "© HARNO — personal study only", False,
        "https://eis.harno.ee/publicitems",
        "Official practice tasks, A2-C1 reading and listening, no login needed.",
    ),
    Source(
        "ekilex-wordlist", "Enriched Ekilex wordlist", "file",
        "CC-BY-SA-4.0", True,
        "https://github.com/KristjanPikhof/Estonian-Wordlist-Enriched-Ekilex",
        "CEFR levels and frequency for 160k lemmas.",
    ),
    Source(
        "sonapi", "Sõnaveeb via api.sonapi.ee", "api",
        "Ekilex data CC-BY-4.0; third-party endpoint", True,
        "https://api.sonapi.ee/v2/",
        "Inflection type, rection, definitions, examples. Single lookups only "
        "— never batch, the upstream asks not to be crawled.",
    ),
    Source(
        "tartunlp-tts", "TartuNLP kõnesüntees", "api",
        "University of Tartu public API", True,
        "https://api.tartunlp.ai/text-to-speech/v2",
        "Turns any text into listening practice. 14 voices, 0.7x for learners.",
    ),
    Source(
        "selges-keeles", "Selges keeles — lihtne eesti keel", "api",
        "© the authors — no explicit reuse licence; personal study only", False,
        "https://selgeskeeles.wordpress.com",
        "349 simplified Estonian news posts, 35-80 words each, 100% Estonian. "
        "Fetched via WordPress.com's public API. Dormant since 2018, which "
        "makes it a fixed corpus — harvest once.",
    ),
    Source(
        "evkk", "EVKK — eesti vahekeele korpus (TLU)", "harvest",
        "taxonomy + counts stored; no explicit reuse licence on the corpus", False,
        "https://evkk.tlu.ee/vers1",
        "51k linguist-annotated errors in learner Estonian. Only the public "
        "error taxonomy and its counts are stored, to weight the curriculum by "
        "what learners actually get wrong. The learner texts are not fetched.",
    ),
    Source(
        "generated", "Genereeritud harjutused", "generated",
        "own work", True, None,
        "Drills built from Vabamorf forms. Unlimited, deterministic.",
    ),
)


def available(path: Path | str) -> bool:
    """Whether the harvested library is actually there.

    Reported by `/api/health`, so "the reading list is empty" can be told apart
    from "the reading list is broken" without reading logs.
    """
    target = Path(path)
    return target.exists() and target.stat().st_size > 0


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
            " (id,source_id,skill,level,title,body,audio_url,meta,added_on)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (i.id, i.source_id, i.skill, i.level, i.title, i.body,
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


def query(
    conn: sqlite3.Connection,
    skill: str | None = None,
    level: str | None = None,
    public_only: bool = False,
    limit: int = 50,
) -> list[sqlite3.Row]:
    """Fetch study items.

    `public_only=True` is what a public, unauthenticated request must use. It is
    a filter on the source's licence, not on anything about the item, so a new
    source cannot leak by forgetting to tag its items.
    """
    where, params = ["1=1"], []
    if skill:
        where.append("i.skill = ?")
        params.append(skill)
    if level:
        where.append("i.level = ?")
        params.append(level)
    if public_only:
        where.append("s.redistributable = 1")
    params.append(limit)
    return list(
        conn.execute(
            f"""SELECT i.*, s.name AS source_name, s.licence, s.redistributable
                FROM items i JOIN sources s ON s.id = i.source_id
                WHERE {' AND '.join(where)}
                ORDER BY i.added_on DESC LIMIT ?""",
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
