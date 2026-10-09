"""Reversible course navigation, separate from assessed knowledge.

The evidence log owns these choices. The progress database only projects them;
skipping creates no attempt, mastery, review card or readiness score.
"""

from __future__ import annotations

import sqlite3

from . import evidence

SCHEMA = """
CREATE TABLE IF NOT EXISTS course_choices (
    topic TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    at TEXT NOT NULL
);
"""


def skipped(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT topic FROM course_choices")}


def _skip(conn: sqlite3.Connection, topic: str, skip: bool, at: str) -> None:
    with conn:
        if skip:
            conn.execute(
                "INSERT INTO course_choices(topic,source,at) VALUES (?,?,?)"
                " ON CONFLICT(topic) DO UPDATE SET source=excluded.source,at=excluded.at",
                (topic, "manual", at),
            )
        else:
            conn.execute("DELETE FROM course_choices WHERE topic=?", (topic,))


def set_skip(conn: sqlite3.Connection, topic: str, skip: bool) -> None:
    from .curriculum import by_id

    by_id(topic)  # Unknown identities must never enter a learner's log.
    ev = evidence.record("course-topic-skipped", {"topic": topic, "skip": skip})
    _skip(conn, topic, skip, ev.ts)


@evidence.applies("course-topic-skipped")
def _apply_skip(stores, ev) -> None:
    _skip(stores["progress"], ev.payload["topic"], ev.payload["skip"], ev.ts)


#: The unit stages a chosen start moves past (`eesti/units.py`).
EARLIER_STAGES = {"a1": {"algus"}, "a1-a2": {"algus"}, "a2": {"algus", "A1"},
                  "a2-b1": {"algus", "A1", "A2"}}


def apply_start(conn: sqlite3.Connection, payload: dict, at: str) -> None:
    """A selected starting point moves navigation past the units of earlier stages.

    Old onboarding events remain recommendations. Only events explicitly carrying
    `navigate` change the course. Manual skips survive changing the starting point.
    Replay re-applies the start, so a unit added later before the learner's stage
    is moved past too.
    """
    if not payload.get("navigate"):
        return
    from .curriculum import TOPICS
    from .units import stage_of

    earlier = EARLIER_STAGES.get(payload["start_band"], set())
    with conn:
        conn.execute("DELETE FROM course_choices WHERE source='start'")
        if not payload.get("skipped"):
            conn.executemany(
                "INSERT OR IGNORE INTO course_choices(topic,source,at) VALUES (?,?,?)",
                [(topic.id, "start", at) for topic in TOPICS
                 if stage_of(topic.id) in earlier],
            )
