"""Spaced repetition over the errors you actually made.

What the 2026 apps get right, and what they cannot do
-----------------------------------------------------
The consistent finding across current reviews is that people abandon streak-based
apps when "the streak no longer improves the skill they care about", and that the
tools which work pair **spaced repetition** with **real content you met yourself**
— Migaku and LingQ build cards from the sentence you were actually reading, so
recall reloads the context.

Both are worth copying. But they build *vocabulary* cards, because a general tool
cannot know why a word was hard. This app can: Vabamorf knows `raamatut` is the
partitive of `raamat`, and the error log knows partitive-for-genitive is the
learner's documented weakness. So a word met while reading becomes a **grammar**
card for the pattern behind it, not just a translation to memorise.

Scheduling uses FSRS-6 via `py-fsrs` (MIT) rather than a hand-rolled interval
scheme. It models difficulty, stability and retrievability per item and needs
20-30% fewer reviews than SM-2 for the same retention — there is no reason to
invent a worse scheduler.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fsrs import Card, Rating, Scheduler

# What the four buttons mean here. FSRS expects a self-rating; the drill loop
# grades objectively, so a wrong answer maps to Again and a correct one to Good.
# Hard/Easy stay available for manual review of reading items.
RATINGS = {"again": Rating.Again, "hard": Rating.Hard, "good": Rating.Good,
           "easy": Rating.Easy}

# How far past the requested count to look when building an interleaved session.
# Wide enough that several topics are in view even when one has a long overdue
# run; capped so a large backlog is never loaded whole.
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


# One-time repair of explanations already in the queue.
#
# `omastav` was being written as **омастав** -- a spelling in neither language,
# which a learner can look up nowhere. Fixing the generators corrects what is
# produced from now on and reaches none of the rows already stored, and this is
# a spaced-repetition queue: those items are guaranteed to come back. So the
# text is repaired where it sits. Idempotent -- the replaced form contains no
# match, so a second run changes nothing.
REPAIRS = (
    ("основы омастава", "основы генитива (omastav)"),
    ("основа омастава", "основа генитива (omastav)"),
    ("а не омастав ", "а не **omastav** "),
)


def repair_explanations(conn: sqlite3.Connection) -> int:
    """Rewrite stored `why_ru` that transliterated an Estonian grammar term.

    Looks before it writes. Running the UPDATE unconditionally turned every
    open of the queue -- including the read-only ones behind `GET /api/status`
    -- into a writer, and a second connection anywhere in the process then got
    `database is locked`. There is nothing to repair on all but the first open,
    so the write happens once and every later open pays only the check.

    That check is a `LIKE '%...%'`, which cannot use an index and scans the
    table -- fine against one learner's queue, and cheap next to the lock
    contention it removes, but it is a scan and not a lookup.
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


def _scheduler() -> Scheduler:
    # Default parameters were trained on ~700M reviews; personal optimisation
    # needs a review history we do not have yet, so defaults are the right start.
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

    That last part matters: meeting `raamatut` again in another text must not
    reset the memory model built from earlier reviews.
    """
    key = item_id(kind, lemma, tag)
    existing = conn.execute(
        "SELECT 1 FROM review_items WHERE id = ?", (key,)
    ).fetchone()
    if existing:
        return key

    card = Card()
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

    Without this the queue is interleaved only by accident. Items enter in
    batches — six seeded the moment a topic is mastered — so they carry
    near-identical due times, and ordering by due date hands them back in the
    order they went in: all of one topic, then all of the next. That is
    *blocked* review, which is precisely what the practice phase already did and
    what the handoff exists to stop doing.

    Mixing here rather than in the scheduler is deliberate. FSRS decides *when*
    an item should come back and is good at it; nothing about its answer changes
    if two items due the same minute swap places. This reorders within what is
    already due, so it costs the scheduler nothing.
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
    """Items ready for review: the most overdue, dealt out across topics.

    Selection is by due date — the scheduler's judgement, untouched. Only the
    order they are asked in is mixed, so a session interleaves instead of
    marching through one topic at a time.
    """
    now = datetime.now(timezone.utc).isoformat()
    sql = "SELECT * FROM review_items WHERE due <= ?"
    params: list = [now]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    # Over-fetch, then interleave, then truncate. Applying LIMIT first defeats
    # the whole thing: a ten-item session takes the ten most overdue, which are
    # the ten that entered together, which is one topic — and there is nothing
    # left to mix. Selection is still "the most overdue window"; only the order
    # inside it changes.
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


def grade(conn: sqlite3.Connection, item_id_: str, rating: str) -> dict:
    """Record a review and reschedule. Returns the new due date and interval."""
    if rating not in RATINGS:
        raise ValueError(f"rating must be one of {sorted(RATINGS)}")

    row = conn.execute(
        "SELECT card, reps, lapses FROM review_items WHERE id = ?", (item_id_,)
    ).fetchone()
    if row is None:
        raise KeyError(item_id_)

    card = Card.from_dict(json.loads(row["card"]))
    updated, _log = _scheduler().review_card(card, RATINGS[rating])

    lapses = row["lapses"] + (1 if rating == "again" else 0)
    with conn:
        conn.execute(
            "UPDATE review_items SET card = ?, due = ?, reps = ?, lapses = ?"
            " WHERE id = ?",
            (json.dumps(updated.to_dict()), updated.due.isoformat(),
             row["reps"] + 1, lapses, item_id_),
        )

    interval = updated.due - datetime.now(timezone.utc)
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
            "struggling": struggling}
