"""What the words mean — stored, so the live dictionary is asked once per word, ever.

Drills on words the learner cannot translate teach only morphology, so every
word the learner looks at gets a stored gloss.

Sõnaveeb and Ekilex ask not to be batch-requested. This store is how that is
honoured across Cloud Run cold starts: it lives in `vocab.db`, which the state
snapshot carries, so a word is never re-requested after a restart. Misses are
stored too.

What keeps it from becoming a harvest, in code:

- a word is fetched only when the learner is looking at it (a card, or a drill
  just answered);
- `sonapi` spaces live requests a second apart, under a lock;
- `DAILY_BUDGET` caps new words per day.

Ekilex data is CC BY 4.0; this store is one learner's, behind Access, and never
redistributed (attribution in `licences.py`).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

#: New words that may be looked up in one day. Generous for a person, useless
#: for a scraper: the whole word list would take about three and a half years.
DAILY_BUDGET = 120

SCHEMA = """
CREATE TABLE IF NOT EXISTS word_gloss (
    lemma           TEXT PRIMARY KEY,
    russian         TEXT NOT NULL DEFAULT '',
    -- Sõnaveeb's definition: accurate, and written for a native speaker
    -- consulting a dictionary.
    definition      TEXT,
    rection         TEXT,
    inflection_type TEXT,
    found           INTEGER NOT NULL DEFAULT 1,
    fetched         TEXT NOT NULL
);

-- One row per day, so the cap survives a restart like everything else here.
CREATE TABLE IF NOT EXISTS gloss_budget (
    day   TEXT PRIMARY KEY,
    spent INTEGER NOT NULL DEFAULT 0
);
"""


#: Columns added for Ekilex (learner-level definition `wwLite`, sense CEFR level,
#: which live dictionary answered). `migrate` adds them to a restored `vocab.db`.
LATER_COLUMNS = ("learner_definition", "level", "source")


def migrate(conn: sqlite3.Connection) -> None:
    have = {row[1] for row in conn.execute("PRAGMA table_info(word_gloss)")}
    for column in LATER_COLUMNS:
        if column not in have:
            conn.execute(f"ALTER TABLE word_gloss ADD COLUMN {column} TEXT")


@dataclass(frozen=True)
class Gloss:
    lemma: str
    russian: tuple[str, ...]
    definition: str | None
    rection: str | None
    inflection_type: str | None
    found: bool
    learner_definition: str | None = None
    level: str | None = None
    #: Which live dictionary answered: `ekilex`, or `sonapi` (also every row
    #: from before the column, and the seed's rows, which are marked `seed`
    #: in `fetched`).
    source: str = "sonapi"

    def to_dict(self) -> dict:
        return {
            "lemma": self.lemma,
            "russian": list(self.russian),
            "definition": self.definition,
            "rection": self.rection,
            "inflection_type": self.inflection_type,
            "found": self.found,
        }


def connect(path: Path | str, *, seed_glosses: bool = True) -> sqlite3.Connection:
    """Open the store in `vocab.db`, which the state snapshot carries.

    Delegates to `vocab.connect`, the file's single opener, so both schemas are
    always present.
    """
    from .vocab import connect as open_vocab

    conn = open_vocab(path)
    # Load the shipped glosses once per store, keyed on a marker (not on emptiness),
    # so stores that already hold dictionary answers still get the seed.
    # `seed_glosses=False` is for tests of the store's own mechanics.
    if seed_glosses:
        try:
            if not conn.execute(
                    "SELECT 1 FROM word_gloss WHERE fetched = 'seed' LIMIT 1"
            ).fetchone():
                seed(conn)
        except Exception:  # noqa: BLE001 - a missing seed must never block the app
            pass
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _row_to_gloss(row: sqlite3.Row) -> Gloss:
    return Gloss(
        lemma=row["lemma"],
        russian=tuple(w for w in (row["russian"] or "").split("\x1f") if w),
        definition=row["definition"],
        rection=row["rection"],
        inflection_type=row["inflection_type"],
        found=bool(row["found"]),
        learner_definition=row["learner_definition"] if "learner_definition" in row.keys() else None,
        level=row["level"] if "level" in row.keys() else None,
        source=(row["source"] if "source" in row.keys() else None) or "sonapi",
    )


def stored(conn: sqlite3.Connection, lemma: str) -> Gloss | None:
    """What is already known locally. Never touches the network."""
    row = conn.execute(
        "SELECT * FROM word_gloss WHERE lemma = ?", (lemma,)
    ).fetchone()
    return _row_to_gloss(row) if row else None


def stored_many(
    conn: sqlite3.Connection, lemmas: list[str] | tuple[str, ...]
) -> dict[str, Gloss]:
    """Local lookup for a list of lemmas: a SELECT only, never a live fetch."""
    wanted = [w for w in dict.fromkeys(lemmas) if w]
    if not wanted:
        return {}
    marks = ",".join("?" * len(wanted))
    rows = conn.execute(
        f"SELECT * FROM word_gloss WHERE lemma IN ({marks})", wanted
    ).fetchall()
    return {row["lemma"]: _row_to_gloss(row) for row in rows}


def save(conn: sqlite3.Connection, lemma: str, info) -> Gloss:
    """Record one lookup. `info` is a `sonapi.WordInfo`, or None for a miss."""
    gloss = Gloss(
        lemma=lemma,
        russian=tuple(info.russian[:4]) if info else (),
        definition=(info.definition if info else None),
        rection=(info.rection if info else None),
        inflection_type=(info.inflection_type if info else None),
        found=info is not None,
        learner_definition=getattr(info, "learner_definition", None),
        level=getattr(info, "level", None),
        source=getattr(info, "source", "sonapi"),
    )
    migrate(conn)
    with conn:
        conn.execute(
            """INSERT INTO word_gloss
                 (lemma, russian, definition, rection, inflection_type,
                  found, fetched, learner_definition, level, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(lemma) DO UPDATE SET
                 russian = excluded.russian,
                 definition = excluded.definition,
                 rection = excluded.rection,
                 inflection_type = excluded.inflection_type,
                 found = excluded.found,
                 fetched = excluded.fetched,
                 learner_definition = excluded.learner_definition,
                 level = excluded.level,
                 source = excluded.source""",
            # EKI's learner definitions are reference data beside the word list, not in this
            # table; `/api/enrich` reads both (see `eesti/psv.py`).
            (lemma, "\x1f".join(gloss.russian), gloss.definition,
             gloss.rection, gloss.inflection_type, int(gloss.found), _now(),
             gloss.learner_definition, gloss.level, gloss.source),
        )
    # Read back, so the caller gets what the store now holds.
    return stored(conn, lemma) or gloss


def spent_today(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT spent FROM gloss_budget WHERE day = ?", (_today(),)
    ).fetchone()
    return row["spent"] if row else 0


def budget_left(conn: sqlite3.Connection) -> int:
    return max(0, DAILY_BUDGET - spent_today(conn))


def _spend(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """INSERT INTO gloss_budget (day, spent) VALUES (?, 1)
               ON CONFLICT(day) DO UPDATE SET spent = spent + 1""",
            (_today(),),
        )


#: Provenance markers meaning "filled locally, never asked about": the shipped
#: glossary, which carries only Russian, so `remember()` still asks the live
#: dictionary for senses, rection and muuttüüp.
BASELINES = ("seed",)


def _is_baseline(conn: sqlite3.Connection, lemma: str) -> bool:
    """Whether the stored row was filled locally rather than by a live answer."""
    row = conn.execute(
        "SELECT fetched FROM word_gloss WHERE lemma = ?", (lemma,)).fetchone()
    return bool(row) and row[0] in BASELINES


def remember(conn: sqlite3.Connection, lemma: str) -> Gloss | None:
    """The one place a live lookup may happen: a word in front of the learner.

    Returns what is stored; otherwise asks the live dictionary once, keeps the
    answer (including "no such word") and returns it. Over budget or offline, it
    returns None and the caller shows nothing.
    """
    lemma = (lemma or "").strip()
    if not lemma:
        return None

    hit = stored(conn, lemma)
    # A seeded row carries only Russian; ask anyway (budget permitting) and keep the
    # seed as the fallback.
    if hit is not None and not _is_baseline(conn, lemma):
        return hit
    if budget_left(conn) <= 0:
        return hit

    from .providers import ekilex, sonapi

    # Ekilex when this deployment holds its key; the Sõnaveeb mirror otherwise.
    # Same budget, same store.
    provider = ekilex if ekilex.available() else sonapi
    _spend(conn)  # spent on the attempt, so a failing service cannot be retried
    try:                                   # into a flood
        info = provider.lookup(lemma)
    except Exception:  # noqa: BLE001 - a third party being down is not an error
        # `hit` rather than None: for a seeded word we already have the Russian,
        # and showing nothing because Sõnaveeb is having a bad minute would be a
        # step backwards from where the seed left us.
        return hit
    return save(conn, lemma, info) or hit


def stats(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        """SELECT COUNT(*) AS n,
                  SUM(CASE WHEN found = 1 THEN 1 ELSE 0 END) AS hits,
                  SUM(CASE WHEN russian <> '' THEN 1 ELSE 0 END) AS glossed
           FROM word_gloss"""
    ).fetchone()
    return {
        "words": row["n"] or 0,
        "found": row["hits"] or 0,
        "with_russian": row["glossed"] or 0,
        "budget_left": budget_left(conn),
        "daily_budget": DAILY_BUDGET,
    }

#: Glosses that ship with the app, for the words drills use. Hand-written for this
#: project — never fetched from Sõnaveeb.
SEED = Path(__file__).resolve().parent.parent / "data" / "seed_glossary.tsv"


def seed(conn: sqlite3.Connection, path: Path | str | None = None) -> int:
    """Load the shipped glosses. Returns how many rows were newly written.

    `INSERT OR IGNORE`, so a live dictionary answer already stored wins. Marked
    `fetched = 'seed'` to keep provenance. Idempotent.
    """
    src = Path(path) if path else SEED
    if not src.exists():
        return 0
    rows = []
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lemma, _, russian = line.partition("\t")
        lemma, russian = lemma.strip(), russian.strip()
        if lemma and russian:
            rows.append((lemma, russian, "seed"))
    if not rows:
        return 0
    conn.executescript(SCHEMA)
    before = conn.execute("SELECT COUNT(*) FROM word_gloss").fetchone()[0]
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO word_gloss (lemma, russian, fetched)"
            " VALUES (?, ?, ?)", rows)
    return conn.execute(
        "SELECT COUNT(*) FROM word_gloss").fetchone()[0] - before
