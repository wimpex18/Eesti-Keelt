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
    band: str | None = None
    audio_url: str | None = None
    meta: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Content hash — re-ingesting the same material updates, never duplicates."""
        payload = f"{self.source_id}|{self.title}|{self.body}|{self.audio_url}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


# The registry. Every source this app is allowed to touch, with the licence that
# governs it. Adding a source means making a licence decision, deliberately.
#: The licence ledger. Two kinds of entry live here, and the difference is worth
#: knowing before reading a "nothing produces this" as a gap:
#:
#: * **Corpus producers** — `err-r4`, `err-lihtsad`, `harno`, `eis`,
#:   `selges-keeles`, `oma-materjal`. A harvester (or `cli ingest`) writes rows
#:   into `items` carrying the id, and `add_items` refuses any id not listed
#:   here. That refusal is the gate.
#: * **Provenance records** — `ekilex-wordlist` (fills `words`), `taltech-gec`
#:   (the attested word-order corrections), `evkk` (an error taxonomy),
#:   `sonapi` and `tartunlp-tts` (live APIs, answers cached not archived),
#:   `ekk` (linked to, with 62 lexical facts stored), `generated` (drills, which
#:   are computed and never stored). Nothing writes `items` for these, and that
#:   is correct: they are here because this project touches them and every
#:   third party it touches has to have its licence written down.
#:
#: `tests/test_sections.py` checks the ledger covers every source id the code
#: writes; it cannot check the second kind, which is why they are named here.
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
        "taltech-gec", "TalTechNLP grammar_et (learner corrections)", "file",
        "no licence stated — personal study only", False,
        "https://huggingface.co/datasets/TalTechNLP/grammar_et",
        "1 000 (learner wrote, native corrected) sentence pairs from the "
        "Estonian Native LLM Benchmark. 47 of them are pure re-orderings, "
        "which is the only sound source of word-order drills this project "
        "has: correctness is attested rather than inferred. The dataset card "
        "states no licence at all, so it is treated as ungranted — same "
        "posture as ERR and HARNO, and never baked into the image.",
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
        "Inflection type, rection, Russian glosses, definitions. Single lookups "
        "only — never batch, the upstream asks not to be crawled. Answers are "
        "kept in vocab.db (eesti/gloss.py) so a word is asked about once ever, "
        "capped per day, and the store is private to one learner behind Access "
        "— never redistributed.",
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
        "ekk", "Eesti keele käsiraamat (EKI)", "file",
        "© Eesti Keele Instituut — linked to, not reproduced", False,
        "https://arhiiv.eki.ee/books/ekk09/index.php",
        "The handbook this project points at instead of restating grammar. Two "
        "uses, both deliberate: every rule explanation links to its section "
        "rather than paraphrasing it, and SÜ 64 — the handbook's own list of "
        "rections people get wrong — is fetched once for 62 lexical facts "
        "(headword, correct frame, marked wrong frame). EKK's example "
        "sentences are **not** stored; rection drills are built over the "
        "harvested corpus instead, so nothing of the prose is reproduced and "
        "the sentences sit at the learner's level rather than the handbook's. "
        "It was the one third party the app uses that this ledger did not "
        "record, found by asking which source ids the code writes.",
    ),
    Source(
        "oma-materjal", "Oma materjal — käsitsi lisatud", "file",
        "unknown, and treated as ungranted — personal study only", False, None,
        "A textbook chapter, a tutor's handout, a transcript typed up by hand: "
        "whatever the learner puts in with `cli ingest`. Not redistributable, "
        "and deliberately not guessed at: this project has no way to know what "
        "licence a file dropped into it carries, and the safe assumption for "
        "somebody else's textbook is the same one it makes about HARNO and "
        "ERR — owner-only, never republished, never baked into the image.",
    ),
    Source(
        "generated", "Genereeritud harjutused", "generated",
        "own work", True, None,
        "Drills built from Vabamorf forms. Unlimited, deterministic.",
    ),
)


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
