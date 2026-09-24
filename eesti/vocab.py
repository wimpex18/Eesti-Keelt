"""Known-word tracking, so the library adapts to what you actually know.

Modelled on Lute/LWT: every word carries a status, and the share of known words
decides whether a text is worth reading. Status is per **lemma** (Vabamorf
resolves `raamatut`, `raamatu`, `raamatud` to one word).

    0  unknown     never seen (implicit — absent from the table)
    1  learning    met, still opaque
    5  known       produced without effort
    98 ignored     "Pole vaja" — excluded from study and counts
    99 well-known  known before this app existed
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# The code uses two thresholds: `>= 1` is *met*, `>= 5` is *settled*. `LEARNING`
# is set by meeting a word; the three settled values are set by the learner.
UNKNOWN, LEARNING, KNOWN, IGNORED, WELL_KNOWN = 0, 1, 5, 98, 99

STATUS_NAMES = {
    LEARNING: "õpin",
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
    """Open `vocab.db` with both of its schemas applied: word status here and word
    meanings in `eesti/gloss.py` share one file, which the state snapshot ships.
    """
    from . import gloss

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA + gloss.SCHEMA)
    gloss.migrate(conn)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_status(conn: sqlite3.Connection, lemma: str, status: int) -> None:
    """Set a lemma's status, preserving how often and when it was met."""
    from . import evidence

    if status not in STATUS_NAMES:
        raise ValueError(f"status must be one of {sorted(STATUS_NAMES)}")
    ev = evidence.record("word-status", {"lemma": lemma, "status": status})
    _set_status(conn, lemma, status, ev.ts)


def _set_status(conn: sqlite3.Connection, lemma: str, status: int, now: str) -> None:
    with conn:
        conn.execute(
            """INSERT INTO vocab_status (lemma, status, met_count, first_seen, last_seen)
               VALUES (?,?,1,?,?)
               ON CONFLICT(lemma) DO UPDATE SET status = excluded.status,
                                                last_seen = excluded.last_seen""",
            (lemma, status, now, now),
        )


def record_encounter(conn: sqlite3.Connection, lemmas: list[str]) -> int:
    """Note that these lemmas were met, without changing any status. Marking a word
    known stays an explicit act.
    """
    from . import evidence

    if not lemmas:
        return 0
    ev = evidence.record("encounter", {"lemmas": list(lemmas)})
    return _encounter(conn, list(lemmas), ev.ts)


def _encounter(conn: sqlite3.Connection, lemmas: list[str], now: str) -> int:
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
    """What share of a text you already handle; ignored words count on neither side."""
    if not lemmas:
        return {"total": 0, "known": 0, "coverage": 0.0}

    unique = sorted(set(lemmas))
    by_lemma = statuses(conn, unique)
    counted = [w for w in unique if by_lemma[w] != IGNORED]
    known = [w for w in counted if by_lemma[w] in (KNOWN, WELL_KNOWN)]
    learning = [w for w in counted if by_lemma[w] == LEARNING]

    return {
        "total": len(counted),
        "known": len(known),
        "learning": len(learning),
        "unknown": len(counted) - len(known) - len(learning),
        "coverage": round(len(known) / len(counted), 3) if counted else 0.0,
    }


# Bands of 500 by frequency rank: small enough to finish, large enough to matter.
BAND_SIZE = 500
BAND_TOP = 4000


def band_progress(
    conn: sqlite3.Connection,
    words: sqlite3.Connection,
    size: int = BAND_SIZE,
    top: int = BAND_TOP,
) -> list[dict]:
    """Known words per frequency band.

    "1 200 of the top 2 000" is meaningful where "12 % of Estonian" is not. `top`
    defaults to 4 000, roughly the A1–B1 vocabulary. Unranked lemmas are excluded.
    """
    settled = {
        r[0] for r in conn.execute(
            f"SELECT lemma FROM vocab_status WHERE status IN "
            f"({','.join(str(s) for s in sorted(SETTLED - {IGNORED}))})"
        )
    }
    out: list[dict] = []
    for start in range(1, top + 1, size):
        end = min(start + size - 1, top)
        band = [
            r[0] for r in words.execute(
                "SELECT word FROM words WHERE freq_rank BETWEEN ? AND ?"
                " AND freq_rank > 0",
                (start, end),
            )
        ]
        known = sum(1 for w in band if w in settled)
        out.append({
            "from": start, "to": end, "size": len(band), "known": known,
            "share": round(known / len(band), 3) if band else 0.0,
        })
    return out


def summary(conn: sqlite3.Connection) -> dict:
    counts = dict(
        conn.execute("SELECT status, COUNT(*) FROM vocab_status GROUP BY status")
    )
    return {
        "by_status": {STATUS_NAMES.get(k, str(k)): v for k, v in counts.items()},
        "known_total": sum(v for k, v in counts.items() if k in (KNOWN, WELL_KNOWN)),
        "tracked": sum(counts.values()),
    }


#: Browse filters. `level` is CEFR, carried only by the tagged A1–B1 minority.
LEVELS = ("A1", "A2", "B1", "B2", "C1")

#: Parts of speech offered. `pos` may be compound (`adj,s`), so a filter matches
#: one comma-separated part.
POS_NAMES = {
    "s": "nimisõna",
    "v": "tegusõna",
    "adj": "omadussõna",
    "adv": "määrsõna",
}


def browse(
    words: sqlite3.Connection,
    store: sqlite3.Connection,
    *,
    level: str | None = None,
    pos: str | None = None,
    status: str | None = None,
    limit: int = 60,
    offset: int = 0,
) -> dict:
    """List vocabulary the learner can work through, commonest first.

    Unranked words sort last. Both connections are passed in: `words` (word list)
    and `store` (this learner's statuses and glosses) are different databases.
    """
    where, args = [], []
    if level:
        if level not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS}")
        where.append("w.proficiency = ?")
        args.append(level)
    if pos:
        # `pos` is a comma-separated tag list; match a whole element of it.
        where.append(
            "(',' || REPLACE(w.pos, ' ', '') || ',') LIKE '%,' || ? || ',%'")
        args.append(pos)

    sql = (
        "SELECT w.word, w.proficiency, w.pos, w.freq_rank,"
        "       c.genitive, c.partitive, c.distinct_"
        "  FROM words w"
        "  LEFT JOIN object_cases c ON c.word = w.word"
        + (" WHERE " + " AND ".join(where) if where else "")
        # Unranked is 0 in this dataset; sort both 0 and NULL last.
        + " ORDER BY (w.freq_rank IS NULL OR w.freq_rank = 0),"
          " w.freq_rank, w.word"
    )

    # Status lives in the other database, so filter after reading: keep reading
    # windows until the page is full. `known` covers both settled-positive rungs;
    # `ignored` lets a "Pole vaja" decision be listed and undone.
    wanted = None
    if status is not None:
        wanted = {
            "new": {UNKNOWN},
            "learning": {LEARNING},
            "known": {KNOWN, WELL_KNOWN},
            "well_known": {WELL_KNOWN},
            "ignored": {IGNORED},
        }.get(status)
        if wanted is None:
            raise ValueError(
                "status must be new, learning, known, well_known or ignored")

    # Every status but "new" is stored, so its words can be named up front and
    # the word list read only for them: filtering window by window scans the whole
    # 160 000-word list when the learner has marked a few dozen.
    if wanted is not None and UNKNOWN not in wanted:
        marked = [r[0] for r in store.execute(
            f"SELECT lemma FROM vocab_status WHERE status IN ({','.join('?' * len(wanted))})",
            sorted(wanted))]
        if not marked:
            return {"items": [], "count": 0, "offset": offset, "more": False,
                    "level": level, "pos": pos, "status": status}
        sql = sql.replace(" ORDER BY", (" AND " if where else " WHERE ")
                          + f"w.word IN ({','.join('?' * len(marked))}) ORDER BY", 1)
        args = [*args, *marked]

    out: list[dict] = []
    seen = 0
    chunk = max(limit * 4, 200)
    while len(out) < limit + offset:
        rows = words.execute(
            sql + " LIMIT ? OFFSET ?", (*args, chunk, seen)).fetchall()
        if not rows:
            break
        seen += len(rows)
        marks = statuses(store, [r[0] for r in rows])
        glosses = _glosses(words, store, [r[0] for r in rows])
        for word, prof, part, rank, gen, par, distinct in rows:
            mark = marks.get(word, UNKNOWN)
            if wanted is not None and mark not in wanted:
                continue
            out.append({
                "word": word,
                "level": prof or None,
                "pos": part or None,
                "pos_name": POS_NAMES.get((part or "").split(",")[0]),
                "freq_rank": rank,
                "status": mark,
                "status_name": STATUS_NAMES.get(mark, "uus"),
                "russian": glosses.get(word, ""),
                # Only worth showing where the two forms differ: that contrast
                # is the whole of `obj-case`, and where they coincide there is
                # nothing to notice.
                "genitive": gen if distinct else None,
                "partitive": par if distinct else None,
            })
    page = out[offset:offset + limit]
    return {
        "items": page,
        "count": len(page),
        "offset": offset,
        # `more` reports whether another page exists, without counting every match.
        "more": len(out) > offset + limit,
        "level": level,
        "pos": pos,
        "status": status,
    }


def _glosses(words: sqlite3.Connection, store: sqlite3.Connection,
             lemmas: list[str]) -> dict[str, str]:
    """Russian for a page of words, from local tables only, in `meaning.py`'s order.
    Never fetches: browsing must not become a batch of live lookups.
    """
    from .meaning import russian_many

    return {k: ", ".join(v) for k, v in russian_many(words, store, lemmas).items()}


def _register() -> None:
    from . import evidence

    @evidence.applies("word-status")
    def _apply_status(stores, ev) -> None:
        _set_status(stores["vocab"], ev.payload["lemma"], ev.payload["status"], ev.ts)

    @evidence.applies("encounter")
    def _apply_encounter(stores, ev) -> None:
        _encounter(stores["vocab"], ev.payload["lemmas"], ev.ts)


_register()
