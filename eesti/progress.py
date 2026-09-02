"""Mastery and progress: what turns a drill box into a course.

Step 3 of the curriculum plan. The topic graph says what *may* be studied; this
says what *has* been, and it is the piece that makes the other steps possible —
"skip what I already know" (step 4) and the blocked-to-interleaved handoff
(step 5) are both reads against this table.

## Advancement is earned, not clicked

The standard shape in course software, and the one the research supports, is
**n correct out of the last m attempts** rather than "you have seen this page".
Here that is 8 of the last 10, with two conditions on the window: it must be
**full**, because a 3/3 is not evidence about a paradigm, and it must cover at
least **five different items**, because otherwise the same two can be answered
five times each and clear the gate — ten attempts, eight correct, window full,
and nothing demonstrated but short-term memory.

Using a *rolling window* rather than lifetime accuracy matters. A learner who got
their first twenty attempts wrong and their last twenty right has learned the
topic, and a lifetime ratio would say 50 % forever and never let them past.

## Mastery does not get revoked

`mastered_at` is a durable fact: on this date you passed the gate. A later bad
run lowers the topic's current accuracy and brings its items back through the
review scheduler, but it does **not** clear the flag, because prerequisites are
what unlock the rest of the syllabus — and revoking them would let one bad
evening lock the learner out of half the course. Forgetting is FSRS's job;
sequencing is this module's, and they should not be wired to fight.

## Skipping and passing are the same operation

A topic marked known by a placement test and a topic mastered by practice differ
only in the `via` column. That is deliberate: the graph in `curriculum.py` reads
`mastered()` and does not care how a topic got there, which is what lets step 4
reuse this gate as a test-out instead of building a parallel one.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# 8 of the last 10. The window must be full — a topic answered three times has
# not demonstrated anything about a paradigm, however clean the three were.
MASTERY_CORRECT = 8
MASTERY_WINDOW = 10

# ...and it must contain this many *different* items. Without it the gate can be
# passed by answering the same two items five times each: ten attempts, eight
# correct, window full, mastered — having demonstrated nothing about the
# paradigm and everything about short-term memory. `item_key` was being stored
# and never read, which is what made the hole invisible. A normal ten-item
# session produces ten distinct items, so this costs an honest learner nothing.
MASTERY_DISTINCT = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    topic    TEXT NOT NULL,
    item_key TEXT NOT NULL,          -- stable hash of the item, for repeat detection
    correct  INTEGER NOT NULL,
    answer   TEXT,                   -- what was actually typed, for the error log
    at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_topic ON attempts(topic, id);

CREATE TABLE IF NOT EXISTS topic_state (
    topic       TEXT PRIMARY KEY,
    mastered_at TEXT,
    via         TEXT,                -- practice | placement
    last_seen   TEXT
);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def item_key(item) -> str:
    """Stable identity for a generated item.

    Items are generated rather than stored, so there is no row id to point at.
    The prompt and answer together identify one, and hashing keeps the column
    short and the same across runs.
    """
    payload = f"{item.topic}|{item.prompt}|{item.answer}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record(conn: sqlite3.Connection, item, correct: bool, answer: str = "") -> None:
    """Log one graded attempt and promote the topic if the gate is now passed."""
    with conn:
        conn.execute(
            "INSERT INTO attempts (topic,item_key,correct,answer,at)"
            " VALUES (?,?,?,?,?)",
            (item.topic, item_key(item), int(correct), answer, _now()),
        )
        conn.execute(
            "INSERT INTO topic_state (topic,last_seen) VALUES (?,?)"
            " ON CONFLICT(topic) DO UPDATE SET last_seen = excluded.last_seen",
            (item.topic, _now()),
        )
    if correct and not is_mastered(conn, item.topic):
        if _window_passes(conn, item.topic):
            mark_mastered(conn, item.topic, via="practice")


def recent(conn: sqlite3.Connection, topic: str, window: int = MASTERY_WINDOW) -> list[int]:
    """The last `window` results for a topic, oldest first."""
    rows = conn.execute(
        "SELECT correct FROM attempts WHERE topic = ? ORDER BY id DESC LIMIT ?",
        (topic, window),
    ).fetchall()
    return [r[0] for r in reversed(rows)]


def accuracy(conn: sqlite3.Connection, topic: str, window: int = MASTERY_WINDOW) -> float | None:
    """Rolling accuracy, or None if the topic has never been attempted.

    None rather than 0.0 deliberately: "not started" and "got everything wrong"
    are different states, and a progress view that renders them the same is
    lying to the learner about where they stand.
    """
    results = recent(conn, topic, window)
    return sum(results) / len(results) if results else None


def distinct_recent(
    conn: sqlite3.Connection, topic: str, window: int = MASTERY_WINDOW
) -> int:
    """How many different items the last `window` attempts covered."""
    return conn.execute(
        "SELECT COUNT(DISTINCT item_key) FROM ("
        "  SELECT item_key FROM attempts WHERE topic = ? ORDER BY id DESC LIMIT ?"
        ")",
        (topic, window),
    ).fetchone()[0]


def _window_passes(conn: sqlite3.Connection, topic: str) -> bool:
    results = recent(conn, topic, MASTERY_WINDOW)
    if len(results) < MASTERY_WINDOW or sum(results) < MASTERY_CORRECT:
        return False
    return distinct_recent(conn, topic) >= MASTERY_DISTINCT


def mark_mastered(conn: sqlite3.Connection, topic: str, via: str = "practice") -> None:
    """Record that the gate was passed. Idempotent — the first date is kept."""
    with conn:
        conn.execute(
            "INSERT INTO topic_state (topic,mastered_at,via,last_seen)"
            " VALUES (?,?,?,?)"
            " ON CONFLICT(topic) DO UPDATE SET"
            "   mastered_at = COALESCE(topic_state.mastered_at, excluded.mastered_at),"
            "   via         = COALESCE(topic_state.via, excluded.via),"
            "   last_seen   = excluded.last_seen",
            (topic, _now(), via, _now()),
        )


def is_mastered(conn: sqlite3.Connection, topic: str) -> bool:
    row = conn.execute(
        "SELECT mastered_at FROM topic_state WHERE topic = ?", (topic,)
    ).fetchone()
    return bool(row and row[0])


def mastered(conn: sqlite3.Connection) -> set[str]:
    """Everything passed, however it was passed."""
    return {
        r[0] for r in conn.execute(
            "SELECT topic FROM topic_state WHERE mastered_at IS NOT NULL"
        )
    }


def reference_topics() -> set[str]:
    """Topics with no generator, which therefore cannot gate anything.

    `pohivormid` and `lauseehitus` are real prerequisites and have no practice
    behind them yet, so requiring them to be *demonstrated* made every topic
    downstream permanently unreachable — the graph offered `tahestik` forever
    and `gen-stem` never. That is a defect in the model, not a fact about
    Estonian: a topic that cannot be tested cannot be a gate.

    They stay in the syllabus and show as `reference`, so they read as material
    to work through rather than quietly disappearing. When step 2 gives one a
    generator it starts gating for real, with no change here.
    """
    from .curriculum import TOPICS

    return {t.id for t in TOPICS if t.generator is None}


def unlocked(conn: sqlite3.Connection) -> set[str]:
    """What counts as satisfied when deciding availability."""
    return mastered(conn) | reference_topics()


@dataclass(frozen=True)
class TopicProgress:
    topic: str
    level: str
    et: str
    attempts: int
    accuracy: float | None
    mastered_at: str | None
    via: str | None
    available: bool
    blocked_by: tuple[str, ...]

    drillable: bool = True

    @property
    def state(self) -> str:
        if self.mastered_at:
            return "mastered"
        if not self.drillable:
            return "reference"
        if not self.available:
            return "locked"
        return "in progress" if self.attempts else "ready"


def report(conn: sqlite3.Connection) -> list[TopicProgress]:
    """Every topic in study order, with where the learner stands on it."""
    from .curriculum import TOPICS, blocked_by, order

    done = unlocked(conn)
    counts = {
        r[0]: r[1] for r in conn.execute(
            "SELECT topic, COUNT(*) FROM attempts GROUP BY topic"
        )
    }
    state = {
        r["topic"]: r for r in conn.execute("SELECT * FROM topic_state")
    }
    known_ids = {t.id for t in TOPICS}

    out: list[TopicProgress] = []
    for topic in order():
        row = state.get(topic.id)
        missing = tuple(b for b in blocked_by(topic.id, done) if b in known_ids)
        out.append(
            TopicProgress(
                topic=topic.id,
                level=topic.level,
                et=topic.et,
                attempts=counts.get(topic.id, 0),
                accuracy=accuracy(conn, topic.id),
                mastered_at=row["mastered_at"] if row else None,
                via=row["via"] if row else None,
                available=not missing,
                blocked_by=missing,
                drillable=topic.generator is not None,
            )
        )
    return out


def resume(conn: sqlite3.Connection) -> str | None:
    """Where to pick up: the first unmastered topic whose prerequisites are met.

    Duolingo's path beat its tree because removing the choice improved outcomes.
    The graph still permits several topics at once; this names one of them so
    the learner does not have to decide before they can start.
    """
    from .curriculum import available

    ready = available(unlocked(conn))
    # A topic with no generator has nothing to practise, so resuming to it
    # hands the learner an empty screen. `tahestik` is the first thing the
    # graph offers and is reference material; it must not be the answer to
    # "where do I pick up".
    drillable = [t for t in ready if t.generator]
    if not drillable:
        return None

    # Prefer something already started over something new — finishing a topic
    # beats accumulating half-done ones.
    started = {r[0] for r in conn.execute("SELECT DISTINCT topic FROM attempts")}
    for topic in drillable:
        if topic.id in started:
            return topic.id
    return drillable[0].id


def reset(conn: sqlite3.Connection, topic: str | None = None) -> dict:
    """Forget attempts, so a topic starts again from nothing.

    Written because I needed it: smoke-testing the deployed app meant answering
    two real questions, and those two attempts went into the learner's own
    record. Two rows out of a ten-attempt mastery window is not nothing — it is
    twenty percent of the evidence the gate is weighing.

    Useful beyond that, though. A topic answered carelessly on a phone, or
    drilled before its prerequisites were understood, leaves a window that says
    "not mastered" for the next ten questions regardless of how well they go.
    Being able to say "start this one over" is the honest fix; quietly adjusting
    the threshold would not be.

    Topic-scoped by default and never implicit: clearing everything requires
    asking for everything.

    **And "everything" now means it.** This cleared `attempts` and `topic_state`
    and left the other three tables in the file standing — `checkpoints`,
    `exposure` and `dictation`, all written by other modules and all read by the
    readiness verdict. So `deploy/reset-progress.sh --everything`, behind a
    "Type ERASE to confirm" prompt, erased a learner's practice history and left
    the app still believing they had passed the A2 checkpoint: `passed_levels`
    returned `{"A2"}` immediately afterwards, and `readiness` gates the whole
    verdict on exactly that.

    The scoped branch stays two tables deliberately, and that is not the same
    omission: a checkpoint is level-wide, exposure is per reading item and a
    dictation is per sentence, so none of them can be attributed to one topic.
    Clearing them for a topic reset would destroy records the request did not
    ask about.

    The full branch is derived from the file rather than listed, because a
    hand-written list of things that exist elsewhere is this repository's
    most-repeated bug and this function is already an instance of it. Every
    table in the learner's progress database *is* learner progress; a sixth one
    added later is covered without anybody remembering to come back here.
    """
    with conn:
        if topic:
            attempts = conn.execute(
                "DELETE FROM attempts WHERE topic = ?", (topic,)
            ).rowcount
            conn.execute("DELETE FROM topic_state WHERE topic = ?", (topic,))
            cleared = ["attempts", "topic_state"]
        else:
            attempts = conn.execute("DELETE FROM attempts").rowcount
            # Names come from `sqlite_master`, never from a caller, so the
            # interpolation below cannot carry anything a user supplied.
            cleared = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
                " AND name NOT LIKE 'sqlite_%'")]
            for name in cleared:
                conn.execute(f"DELETE FROM {name}")  # noqa: S608 - see above
    return {"topic": topic, "attempts_removed": attempts,
            "tables_cleared": sorted(cleared)}
