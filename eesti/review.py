"""Spaced repetition over the errors you actually made.

Like Migaku and LingQ, cards come from material the learner met, but as
**grammar** cards: Vabamorf knows `raamatut` is the partitive of `raamat`, so a
word met while reading becomes a card for the pattern behind it.

Scheduling uses FSRS-6 via `py-fsrs` (MIT).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fsrs import Card, Rating, Scheduler

from . import evidence
from .item import accepts

# FSRS ratings. Grammar cards are rated by code from a typed answer
# (`auto_rating`: wrong -> Again, slow -> Hard, else Good); vocabulary cards,
# which are recall without a typed answer, are rated by the learner.
RATINGS = {"again": Rating.Again, "hard": Rating.Hard, "good": Rating.Good,
           "easy": Rating.Easy}

# How far past the requested count to look when building an interleaved session;
# capped so a large backlog is never loaded whole.
FETCH_FACTOR = 10
FETCH_CAP = 1000

SCHEMA = """
CREATE TABLE IF NOT EXISTS review_items (
    id          TEXT PRIMARY KEY,   -- stable per (kind, lemma, tag)
    kind        TEXT NOT NULL,      -- curriculum topic id, or `vocab`
    lemma       TEXT NOT NULL,
    tag         TEXT,               -- rule or form being tested
    prompt      TEXT NOT NULL,
    answer      TEXT NOT NULL,
    distractor  TEXT,
    why_ru      TEXT,
    source      TEXT,               -- where it came from: drill | reading | error-log
    context     TEXT,               -- the sentence it was met in, if any
    card        TEXT NOT NULL,      -- FSRS card state, JSON
    due         TEXT NOT NULL,      -- ISO-8601, denormalised so the queue is one query
    reps        INTEGER NOT NULL DEFAULT 0,
    lapses      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_due ON review_items(due);
CREATE INDEX IF NOT EXISTS idx_kind ON review_items(kind);
"""


@dataclass(frozen=True)
class ReviewItem:
    id: str
    kind: str
    lemma: str
    prompt: str
    answer: str
    distractor: str | None
    why_ru: str | None
    context: str | None
    due: datetime
    reps: int
    lapses: int


# One-time repair: stored explanations that transliterated `omastav` as
# **омастав** are rewritten in place. Idempotent.
REPAIRS = (
    ("основы омастава", "основы генитива (omastav)"),
    ("основа омастава", "основа генитива (omastav)"),
    ("а не омастав ", "а не **omastav** "),
)


def repair_explanations(conn: sqlite3.Connection) -> int:
    """Rewrite stored `why_ru` that transliterated an Estonian grammar term.

    Checks before writing, so read-only opens never take a write lock. The check is
    an unindexed `LIKE` scan, fine for one learner's queue.
    """
    total = 0
    for bad, good in REPAIRS:
        hit = conn.execute(
            "SELECT 1 FROM review_items WHERE why_ru LIKE '%' || ? || '%' LIMIT 1",
            (bad,),
        ).fetchone()
        if hit is None:
            continue
        cur = conn.execute(
            "UPDATE review_items SET why_ru = replace(why_ru, ?, ?) "
            "WHERE why_ru LIKE '%' || ? || '%'",
            (bad, good, bad),
        )
        total += cur.rowcount or 0
    if total:
        conn.commit()
    return total


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        repair_explanations(conn)
    except sqlite3.OperationalError:
        # Another connection holds the write lock. This is maintenance, not the
        # caller's errand -- it runs on the next open instead of failing a read.
        pass
    return conn


#: Reviews before a personal fit is worth anything. Below this the optimiser
#: fits the noise in a handful of answers and schedules worse than the
#: published defaults, which were fitted on millions of reviews.
MIN_REVIEWS_TO_FIT = 1000


def parameters() -> tuple[float, ...] | None:
    """The learner's own FSRS parameters, if they have ever been fitted.

    Kept in the evidence log (`fsrs-parameters`), not in a file: they are
    derived from the learner's review history, they travel with it, and a
    rebuild replays them. `None` means the published defaults.
    """
    from . import evidence

    try:
        with evidence.connect() as log:
            row = log.execute(
                "SELECT payload FROM events WHERE type = 'fsrs-parameters'"
                " ORDER BY seq DESC LIMIT 1").fetchone()
    except sqlite3.Error:      # no log yet: the defaults are the right answer
        return None
    if row is None:
        return None
    import json as _json

    found = _json.loads(row["payload"]).get("parameters")
    return tuple(found) if found else None


def _scheduler() -> Scheduler:
    """The scheduler, with the learner's own parameters when they exist."""
    fitted = parameters()
    if not fitted:
        return Scheduler()
    try:
        return Scheduler(parameters=fitted)
    except Exception:  # noqa: BLE001 - a bad fit must never stop review
        return Scheduler()


def item_id(kind: str, lemma: str, tag: str | None) -> str:
    return f"{kind}:{lemma}:{tag or ''}"


def add(
    conn: sqlite3.Connection,
    kind: str,
    lemma: str,
    prompt: str,
    answer: str,
    tag: str | None = None,
    distractor: str | None = None,
    why_ru: str | None = None,
    source: str = "drill",
    context: str | None = None,
) -> str:
    """Queue an item for review. Re-adding an existing one keeps its schedule.

    The schedule belongs to the learner and is kept; prompt and answer are
    refreshed from what the app now knows. `context` (the sentence the word was
    first met in) is filled only if empty.
    """
    payload = {"kind": kind, "lemma": lemma, "tag": tag, "prompt": prompt,
               "answer": answer, "distractor": distractor, "why_ru": why_ru,
               "source": source, "context": context}
    ev = evidence.record("card-added", payload)
    return _add(conn, payload, ev.ts)


def _add(conn: sqlite3.Connection, p: dict, at: str) -> str:
    kind, lemma, tag = p["kind"], p["lemma"], p["tag"]
    prompt, answer, distractor = p["prompt"], p["answer"], p["distractor"]
    why_ru, source, context = p["why_ru"], p["source"], p["context"]
    key = item_id(kind, lemma, tag)
    existing = conn.execute(
        "SELECT context FROM review_items WHERE id = ?", (key,)
    ).fetchone()
    if existing:
        with conn:
            conn.execute(
                """UPDATE review_items
                      SET prompt = ?, answer = ?, distractor = ?, why_ru = ?,
                          context = COALESCE(context, ?)
                    WHERE id = ?""",
                (prompt, answer, distractor, why_ru, context, key),
            )
        return key

    # Id and due date from the key and the event, not the clock, so a replay of
    # the log writes the same card.
    card = Card(card_id=evidence.card_id(key), due=datetime.fromisoformat(at))
    with conn:
        conn.execute(
            """INSERT INTO review_items
               (id, kind, lemma, tag, prompt, answer, distractor, why_ru,
                source, context, card, due, reps, lapses)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,0)""",
            (key, kind, lemma, tag, prompt, answer, distractor, why_ru,
             source, context, json.dumps(card.to_dict()),
             card.due.isoformat()),
        )
    return key


def interleave(items: list[ReviewItem]) -> list[ReviewItem]:
    """Deal the queue round-robin by topic, keeping each topic's own order.

    Items enter in batches with near-identical due times, so due-date order alone
    would return one topic at a time. This reorders only within what is due.
    """
    by_kind: dict[str, list[ReviewItem]] = {}
    for item in items:
        by_kind.setdefault(item.kind, []).append(item)

    out: list[ReviewItem] = []
    while by_kind:
        for kind in list(by_kind):
            out.append(by_kind[kind].pop(0))
            if not by_kind[kind]:
                del by_kind[kind]
    return out


def due(conn: sqlite3.Connection, limit: int = 20, kind: str | None = None) -> list[ReviewItem]:
    """Items ready for review: the most overdue, dealt out across topics."""
    now = datetime.now(timezone.utc).isoformat()
    sql = "SELECT * FROM review_items WHERE due <= ?"
    params: list = [now]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    # Over-fetch, interleave, then truncate: truncating first would leave a single
    # topic to mix.
    sql += " ORDER BY due LIMIT ?"
    params.append(limit if kind else min(limit * FETCH_FACTOR, FETCH_CAP))

    items = [
        ReviewItem(
            id=r["id"], kind=r["kind"], lemma=r["lemma"], prompt=r["prompt"],
            answer=r["answer"], distractor=r["distractor"], why_ru=r["why_ru"],
            context=r["context"], due=datetime.fromisoformat(r["due"]),
            reps=r["reps"], lapses=r["lapses"],
        )
        for r in conn.execute(sql, params)
    ]
    # A single-topic request is a deliberate drill-down, so leave it alone.
    return items if kind else interleave(items)[:limit]


@evidence.applies("card-added")
def _apply_add(stores, ev) -> None:
    _add(stores["review"], ev.payload, ev.ts)


#: A correct answer slower than this is rated Hard rather than Good: it was
#: retrieved, but with effort. Fixed until there is latency history to fit.
HARD_AFTER_MS = 15_000


def auto_rating(correct: bool, latency_ms: int | None = None) -> str:
    """The FSRS rating code gives a typed answer. Easy is never automatic."""
    if not correct:
        return "again"
    if latency_ms is not None and latency_ms > HARD_AFTER_MS:
        return "hard"
    return "good"


def grade(conn: sqlite3.Connection, item_id_: str, rating: str, *,
          auto: bool = False, given: str | None = None,
          latency_ms: int | None = None) -> dict:
    """Record a review and reschedule. Returns the new due date and interval.

    The event is the FSRS review log: rating, whether code or the learner chose
    it, and what was typed.
    """
    if rating not in RATINGS:
        raise ValueError(f"rating must be one of {sorted(RATINGS)}")
    if conn.execute("SELECT 1 FROM review_items WHERE id = ?",
                    (item_id_,)).fetchone() is None:
        raise KeyError(item_id_)
    payload = {"id": item_id_, "rating": rating, "auto": auto, "given": given,
               "latency_ms": latency_ms}
    ev = evidence.record("review", payload)
    return _grade(conn, payload, ev.ts)


@evidence.applies("review")
def _apply_grade(stores, ev) -> None:
    _grade(stores["review"], ev.payload, ev.ts)


def answer(conn: sqlite3.Connection, item_id_: str, given: str,
           latency_ms: int | None = None) -> dict:
    """Grade a typed answer to a card and rate it from the result (`auto_rating`)."""
    row = conn.execute(
        "SELECT answer FROM review_items WHERE id = ?", (item_id_,)).fetchone()
    if row is None:
        raise KeyError(item_id_)
    correct = accepts(row["answer"], given)
    rating = auto_rating(correct, latency_ms)
    out = grade(conn, item_id_, rating, auto=True, given=given, latency_ms=latency_ms)
    return out | {"correct": correct, "rating": rating, "answer": row["answer"]}


def _grade(conn: sqlite3.Connection, p: dict, at: str) -> dict:
    item_id_, rating = p["id"], p["rating"]
    row = conn.execute(
        "SELECT card, reps, lapses FROM review_items WHERE id = ?", (item_id_,)
    ).fetchone()
    if row is None:
        raise KeyError(item_id_)

    when = datetime.fromisoformat(at)
    card = Card.from_dict(json.loads(row["card"]))
    updated, _log = _scheduler().review_card(card, RATINGS[rating],
                                             review_datetime=when)

    lapses = row["lapses"] + (1 if rating == "again" else 0)
    with conn:
        conn.execute(
            "UPDATE review_items SET card = ?, due = ?, reps = ?, lapses = ?"
            " WHERE id = ?",
            (json.dumps(updated.to_dict()), updated.due.isoformat(),
             row["reps"] + 1, lapses, item_id_),
        )

    interval = updated.due - when
    return {
        "id": item_id_,
        "due": updated.due.isoformat(),
        "interval_days": round(interval.total_seconds() / 86400, 2),
        "reps": row["reps"] + 1,
        "lapses": lapses,
    }


def stats(conn: sqlite3.Connection) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    total = conn.execute("SELECT COUNT(*) FROM review_items").fetchone()[0]
    ready = conn.execute(
        "SELECT COUNT(*) FROM review_items WHERE due <= ?", (now,)
    ).fetchone()[0]
    by_kind = dict(
        conn.execute("SELECT kind, COUNT(*) FROM review_items GROUP BY kind")
    )
    struggling = [
        dict(r) for r in conn.execute(
            "SELECT lemma, kind, lapses, reps FROM review_items"
            " WHERE lapses > 0 ORDER BY lapses DESC LIMIT 10"
        )
    ]
    return {"total": total, "due": ready, "by_kind": by_kind,
            "struggling": struggling, "forecast": forecast(conn, days=14)}


def forecast(conn: sqlite3.Connection, days: int = 7,
             now: datetime | None = None) -> list[int]:
    """Cards coming due on each of the next `days` days; today includes overdue.

    Days are counted in 24-hour steps from now, so the forecast needs no zone.
    """
    now = now or datetime.now(timezone.utc)
    out = []
    for i in range(days):
        end = (now + timedelta(days=i + 1)).isoformat()
        if i == 0:
            n = conn.execute("SELECT COUNT(*) FROM review_items WHERE due < ?",
                             (end,)).fetchone()[0]
        else:
            begin = (now + timedelta(days=i)).isoformat()
            n = conn.execute("SELECT COUNT(*) FROM review_items WHERE due >= ? AND due < ?",
                             (begin, end)).fetchone()[0]
        out.append(n)
    return out
