"""Mastery and progress: what turns a drill box into a course.

- **Mastery gate:** 8 correct of the last 10 attempts, with the window full and
  at least five distinct items. A rolling window, so early mistakes do not
  block a learner forever.
- **Mastery is not revoked.** `mastered_at` records passing the gate; later
  mistakes bring items back through review (FSRS) but do not re-lock the
  syllabus.
- **Skipping and passing are one operation:** a test-out and practice differ
  only in the `via` column, and `curriculum.py` reads `mastered()` either way.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import evidence

# 8 of the last 10, and the window must be full.
MASTERY_CORRECT = 8
MASTERY_WINDOW = 10

# ...over at least this many distinct items, so repeating two items cannot pass.
MASTERY_DISTINCT = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    topic    TEXT NOT NULL,
    item_key TEXT NOT NULL,          -- stable hash of the item, for repeat detection
    correct  INTEGER NOT NULL,
    answer   TEXT,                   -- what was actually typed, for the error log
    at       TEXT NOT NULL,
    rule     TEXT                    -- the sub-rule asked (obj-case: negation, ...), if any
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
    # `rule` arrived after the first snapshots; a restored database lacks it.
    columns = {r[1] for r in conn.execute("PRAGMA table_info(attempts)")}
    if "rule" not in columns:
        conn.execute("ALTER TABLE attempts ADD COLUMN rule TEXT")
        conn.commit()
    return conn


def item_key(item) -> str:
    """Stable identity for a generated item: a hash of prompt and answer."""
    payload = f"{item.topic}|{item.prompt}|{item.answer}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record(conn: sqlite3.Connection, item, correct: bool, answer: str = "", *,
           ref: dict | None = None, latency_ms: int | None = None,
           mode: str = "path") -> str:
    """Log one graded attempt and promote the topic if the gate is now passed.

    The event carries the whole item as it was shown, and its `ref` (how to
    regenerate it, `eesti/itemref.py`), so the attempt can be replayed later.
    """
    payload = {
        "topic": item.topic, "item_key": item_key(item), "correct": bool(correct),
        "answer": answer, "rule": getattr(item, "rule", "") or None,
        "prompt": item.prompt, "expected": item.answer,
        "lemma": getattr(item, "lemma", "") or "",
        "distractor": getattr(item, "distractor", "") or "",
        "ref": ref, "latency_ms": latency_ms, "mode": mode,
    }
    ev = evidence.record("attempt", payload)
    _attempt(conn, payload, ev.ts)
    # The id, so a caller can point the tutor at exactly this attempt.
    return ev.id


def _attempt(conn: sqlite3.Connection, p: dict, at: str) -> None:
    """The projection of one attempt: the row, `last_seen`, and the gate."""
    with conn:
        conn.execute(
            "INSERT INTO attempts (topic,item_key,correct,answer,at,rule)"
            " VALUES (?,?,?,?,?,?)",
            (p["topic"], p["item_key"], int(p["correct"]), p["answer"], at, p["rule"]),
        )
        conn.execute(
            "INSERT INTO topic_state (topic,last_seen) VALUES (?,?)"
            " ON CONFLICT(topic) DO UPDATE SET last_seen = excluded.last_seen",
            (p["topic"], at),
        )
    if p["correct"] and not is_mastered(conn, p["topic"]):
        if _window_passes(conn, p["topic"]):
            _mark(conn, p["topic"], "practice", at)


@evidence.applies("attempt")
def _apply_attempt(stores, ev) -> None:
    _attempt(stores["progress"], ev.payload, ev.ts)


def recent(conn: sqlite3.Connection, topic: str, window: int = MASTERY_WINDOW) -> list[int]:
    """The last `window` results for a topic, oldest first."""
    rows = conn.execute(
        "SELECT correct FROM attempts WHERE topic = ? ORDER BY id DESC LIMIT ?",
        (topic, window),
    ).fetchall()
    return [r[0] for r in reversed(rows)]


def accuracy(conn: sqlite3.Connection, topic: str, window: int = MASTERY_WINDOW) -> float | None:
    """Rolling accuracy, or None if never attempted ("not started" is not 0 %)."""
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
    """Record that the gate was passed. Idempotent — the first date is kept.

    Practice reaches the gate inside `record`; this is for the other ways of
    passing it (placement, test-out), each an event of its own.
    """
    ev = evidence.record("mastered", {"topic": topic, "via": via})
    _mark(conn, topic, via, ev.ts)


def _mark(conn: sqlite3.Connection, topic: str, via: str, at: str) -> None:
    with conn:
        conn.execute(
            "INSERT INTO topic_state (topic,mastered_at,via,last_seen)"
            " VALUES (?,?,?,?)"
            " ON CONFLICT(topic) DO UPDATE SET"
            "   mastered_at = COALESCE(topic_state.mastered_at, excluded.mastered_at),"
            "   via         = COALESCE(topic_state.via, excluded.via),"
            "   last_seen   = excluded.last_seen",
            (topic, at, via, at),
        )


@evidence.applies("mastered")
def _apply_mastered(stores, ev) -> None:
    _mark(stores["progress"], ev.payload["topic"], ev.payload["via"], ev.ts)


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

    A topic that cannot be tested cannot be a prerequisite gate; these show as
    `reference` and start gating once they get a generator.
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
    """Where to pick up: the first unmastered topic whose prerequisites are met."""
    from .curriculum import available

    ready = available(unlocked(conn))
    # Skip topics with no generator: resuming to one would show an empty screen.
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


#: Repairs already applied, stored in `progress.db` so they travel with the
#: snapshot and run once per database.
REPAIRS_SCHEMA = """
CREATE TABLE IF NOT EXISTS repairs (
    name    TEXT PRIMARY KEY,
    at      TEXT NOT NULL,
    removed INTEGER NOT NULL,
    detail  TEXT NOT NULL
);
"""

#: Named so the record says what it was, not when it ran.
FABRICATED = "placement-fabricated-attempts"


def repair_fabricated_attempts(conn: sqlite3.Connection) -> dict:
    """Remove attempts recorded when nobody was answering.

    Signature: `PROBE_ITEMS` or more attempts sharing one timestamp, all blank and
    all wrong — a person cannot answer five items in one second. Removed rows are
    saved as JSON in `repairs.detail` first. Idempotent by name; runs after a
    restore, not at import, because a restore replaces `progress.db`.
    """
    import json

    from .placement import PROBE_ITEMS

    conn.executescript(REPAIRS_SCHEMA)
    done = conn.execute(
        "SELECT removed FROM repairs WHERE name = ?", (FABRICATED,)).fetchone()
    if done is not None:
        return {"already_applied": True, "removed": done[0]}

    bursts = [
        row[0] for row in conn.execute(
            "SELECT at FROM attempts WHERE answer = '' AND correct = 0"
            " GROUP BY at HAVING COUNT(*) >= ?", (PROBE_ITEMS,))
    ]
    rows = []
    if bursts:
        marks = ",".join("?" * len(bursts))
        rows = [dict(r) for r in conn.execute(
            f"SELECT * FROM attempts WHERE answer = '' AND correct = 0"
            f" AND at IN ({marks})", bursts)]
    with conn:
        if bursts:
            marks = ",".join("?" * len(bursts))
            conn.execute(
                f"DELETE FROM attempts WHERE answer = '' AND correct = 0"
                f" AND at IN ({marks})", bursts)
        conn.execute(
            "INSERT INTO repairs (name, at, removed, detail) VALUES (?,?,?,?)",
            (FABRICATED, _now(), len(rows), json.dumps(rows, ensure_ascii=False)),
        )
    return {"already_applied": False, "removed": len(rows),
            "topics": sorted({r["topic"] for r in rows})}


def reset(conn: sqlite3.Connection, topic: str | None = None) -> dict:
    """Forget attempts, so a topic starts again from nothing.

    Topic-scoped by default: clears that topic's `attempts` and `topic_state`
    (checkpoints, exposure and dictation cannot be attributed to one topic).
    Clearing everything must be asked for, and then clears every table in the file,
    derived from the schema rather than listed.
    """
    evidence.record("progress-reset", {"topic": topic})
    return _reset(conn, topic)


@evidence.applies("progress-reset")
def _apply_reset(stores, ev) -> None:
    _reset(stores["progress"], ev.payload.get("topic"))


def _reset(conn: sqlite3.Connection, topic: str | None) -> dict:
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
