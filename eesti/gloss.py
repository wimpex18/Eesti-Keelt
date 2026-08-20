"""What the words mean — kept, so Sõnaveeb is asked once per word and never again.

## The gap this fills

The app knows 160 316 Estonian words, knows which of them are A1, A2 or B1, and
can inflect any of them. It could not say what a single one of them meant.

That is not an abstract omission. Generate twelve B1 object-case drills and the
lemmas that come back are `etendus`, `luuletus`, `rahakott`, `kingitus`,
`jäätis`, `kleit` — none of which a Russian speaker at A2 knows. The learner
supplies `kleidi` for "Ma ostsin ____", gets it right, and has practised
morphology on a token with no meaning attached. The stated scope of this project
is *learning Estonian*, not only passing an exam, and a drill on a word you
cannot translate teaches half of what it looks like it teaches.

## Why this is not the batch-request the rules forbid

`providers/sonapi.py` says single lookups only, because Sõnaveeb's maintainers
ask not to be batch-requested. That rule stands and this module does not bend
it. It makes it *stronger*, because the honest reading of "do not hammer our
server" is **ask once per word, ever** — and that is precisely what the app was
failing to do.

Its cache lived in `data/cache/sonapi/`, which is git-ignored, not the content
volume, and not in the state snapshot. Cloud Run scales to zero. So every cold
start began with an empty cache, and every word the learner looked at was
requested again — the same words, session after session, because seeing a word
again is the entire point of spaced repetition. The module whose central promise
is "don't hammer Sõnaveeb" had storage that guaranteed it would.

This is the same bug as the circuit breaker keeping its failure counts in a
module-level dict: *state that protects against restarts must survive one*.
Here the state protects a third party, which makes it worse.

## What stops this becoming a harvest

Three things, in code rather than in this docstring:

  * a word is fetched only when the learner is looking at it — reading a card,
    or having just answered a drill on it;
  * `sonapi` still spaces live requests a second apart, under a lock;
  * and `DAILY_BUDGET` caps new words per day. A person meets a few dozen new
    words in a hard study session. At this cap the full 160 316-word list would
    take three and a half years, so no code path here can turn into a harvest
    even by accident.

Misses are stored too. A word Sõnaveeb does not have is a fact worth keeping;
re-asking for it every session is the same load with none of the benefit.

## Licence

Ekilex — the database behind Sõnaveeb, and behind `api.sonapi.ee` — is CC BY 4.0.
This store is private to one learner, behind Cloudflare Access, and travels only
inside their own state snapshot. It is never redistributed, and `sources.py`
records the attribution.
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


@dataclass(frozen=True)
class Gloss:
    lemma: str
    russian: tuple[str, ...]
    definition: str | None
    rection: str | None
    inflection_type: str | None
    found: bool

    def to_dict(self) -> dict:
        return {
            "lemma": self.lemma,
            "russian": list(self.russian),
            "definition": self.definition,
            "rection": self.rection,
            "inflection_type": self.inflection_type,
            "found": self.found,
        }


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the store. Lives in `vocab.db`, which the state snapshot carries.

    Not a file of its own: a gloss is a fact about a word this learner met, it
    is small, and putting it anywhere outside the snapshot would reproduce the
    exact bug this module exists to fix.

    Delegates to `vocab.connect` so the file has exactly one opener and comes
    back complete whichever module asked for it. Two openers, each applying
    half the schema, is how the glossed-word count went missing on a fresh
    container instead of reading zero.
    """
    from .vocab import connect as open_vocab

    return open_vocab(path)


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
    """Local lookup for a list of lemmas.

    A bulk read of the **local** table, which is a SELECT and nothing else.
    Deliberately has no live-fetch fallback: that would be the loop over
    `sonapi` this whole design exists to prevent, wearing a different name.
    """
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
    )
    with conn:
        conn.execute(
            """INSERT INTO word_gloss
                 (lemma, russian, definition, rection, inflection_type,
                  found, fetched)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(lemma) DO UPDATE SET
                 russian = excluded.russian,
                 definition = excluded.definition,
                 rection = excluded.rection,
                 inflection_type = excluded.inflection_type,
                 found = excluded.found,
                 fetched = excluded.fetched""",
            (lemma, "\x1f".join(gloss.russian), gloss.definition,
             gloss.rection, gloss.inflection_type, int(gloss.found), _now()),
        )
    return gloss


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


def remember(conn: sqlite3.Connection, lemma: str) -> Gloss | None:
    """The one place a live lookup may happen: a word in front of the learner.

    Returns what is stored if anything is; otherwise asks Sõnaveeb once, keeps
    the answer — including "no such word" — and returns it. Over budget, or with
    the service down, the answer is None and the caller shows nothing. An
    enrichment is never worth an error, and never worth a wait the learner did
    not ask for.
    """
    lemma = (lemma or "").strip()
    if not lemma:
        return None

    hit = stored(conn, lemma)
    if hit is not None:
        return hit
    if budget_left(conn) <= 0:
        return None

    from .providers import sonapi

    _spend(conn)  # spent on the attempt, so a failing service cannot be retried
    try:                                   # into a flood
        info = sonapi.lookup(lemma)
    except Exception:  # noqa: BLE001 - a third party being down is not an error
        return None
    return save(conn, lemma, info)


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
