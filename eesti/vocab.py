"""Known-word tracking, so the library adapts to what you actually know.

Adapted from Lute/LWT, the open-source ancestor of LingQ's model: every word in
a text carries a status, statuses are visible *while reading*, and the share of
known words is what tells you whether a text is worth your time.

Lute uses 1–5 plus special codes for ignored and well-known. The same shape is
used here, with one change that follows from this app being about grammar rather
than vocabulary: status is tracked **per lemma**, not per surface form. Meeting
`raamatut`, `raamatu` and `raamatud` is meeting one word three times, and
Vabamorf already tells us so. A surface-form tracker would show three unknowns
and badly understate what the reader knows.

    0  unknown     never seen (implicit — absent from the table)
    1  learning    met, still opaque
    3  familiar    recognised in context
    5  known       produced without effort
    98 ignored     names, numbers, foreign words — never counted
    99 well-known  known before this app existed; excluded from study
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

UNKNOWN, LEARNING, FAMILIAR, KNOWN, IGNORED, WELL_KNOWN = 0, 1, 3, 5, 98, 99

STATUS_NAMES = {
    LEARNING: "õpin",
    FAMILIAR: "tuttav",
    KNOWN: "tean",
    IGNORED: "eiran",
    WELL_KNOWN: "teadsin ammu",
}

# Statuses that mean "do not spend study time on this".
SETTLED = frozenset({KNOWN, IGNORED, WELL_KNOWN})

SCHEMA = """
CREATE TABLE IF NOT EXISTS vocab_status (
    lemma      TEXT PRIMARY KEY,
    status     INTEGER NOT NULL,
    met_count  INTEGER NOT NULL DEFAULT 1,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vocab_status ON vocab_status(status);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_status(conn: sqlite3.Connection, lemma: str, status: int) -> None:
    """Set a lemma's status, preserving how often and when it was met."""
    if status not in STATUS_NAMES:
        raise ValueError(f"status must be one of {sorted(STATUS_NAMES)}")
    now = _now()
    with conn:
        conn.execute(
            """INSERT INTO vocab_status (lemma, status, met_count, first_seen, last_seen)
               VALUES (?,?,1,?,?)
               ON CONFLICT(lemma) DO UPDATE SET status = excluded.status,
                                                last_seen = excluded.last_seen""",
            (lemma, status, now, now),
        )


def record_encounter(conn: sqlite3.Connection, lemmas: list[str]) -> int:
    """Note that these lemmas were met, without changing any status.

    Called when a text is opened. Encounters are evidence of exposure; deciding
    a word is known stays an explicit act, because a word skimmed past is not a
    word learned — the mistake that makes automatic "known" counts meaningless.
    """
    if not lemmas:
        return 0
    now = _now()
    with conn:
        conn.executemany(
            """INSERT INTO vocab_status (lemma, status, met_count, first_seen, last_seen)
               VALUES (?,?,1,?,?)
               ON CONFLICT(lemma) DO UPDATE SET met_count = met_count + 1,
                                                last_seen = excluded.last_seen""",
            [(lemma, LEARNING, now, now) for lemma in lemmas],
        )
    return len(lemmas)


def statuses(conn: sqlite3.Connection, lemmas: list[str]) -> dict[str, int]:
    """Status per lemma; absent lemmas are UNKNOWN."""
    if not lemmas:
        return {}
    marks = ",".join("?" * len(lemmas))
    rows = conn.execute(
        f"SELECT lemma, status FROM vocab_status WHERE lemma IN ({marks})", lemmas
    )
    found = {r["lemma"]: r["status"] for r in rows}
    return {lemma: found.get(lemma, UNKNOWN) for lemma in lemmas}


def coverage(conn: sqlite3.Connection, lemmas: list[str]) -> dict:
    """What share of a text you already handle.

    Ignored words are excluded from both sides: a proper name is neither a word
    you know nor one you need, and counting it either way distorts the number
    the reader uses to choose a text.
    """
    if not lemmas:
        return {"total": 0, "known": 0, "coverage": 0.0}

    unique = sorted(set(lemmas))
    by_lemma = statuses(conn, unique)
    counted = [w for w in unique if by_lemma[w] != IGNORED]
    known = [w for w in counted if by_lemma[w] in (KNOWN, WELL_KNOWN)]
    learning = [w for w in counted if by_lemma[w] in (LEARNING, FAMILIAR)]

    return {
        "total": len(counted),
        "known": len(known),
        "learning": len(learning),
        "unknown": len(counted) - len(known) - len(learning),
        "coverage": round(len(known) / len(counted), 3) if counted else 0.0,
    }


def summary(conn: sqlite3.Connection) -> dict:
    counts = dict(
        conn.execute("SELECT status, COUNT(*) FROM vocab_status GROUP BY status")
    )
    return {
        "by_status": {STATUS_NAMES.get(k, str(k)): v for k, v in counts.items()},
        "known_total": sum(v for k, v in counts.items() if k in (KNOWN, WELL_KNOWN)),
        "tracked": sum(counts.values()),
    }
