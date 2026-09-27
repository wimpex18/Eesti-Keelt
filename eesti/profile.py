"""The learner's profile: who they are and how far they have come (ADR-0006).

Derived, like everything else, from the evidence log and the projections; the
only thing stored is the name, as a `profile-set` event. There is no profile
table and no second persistence source. Email is not stored at all: it is the
account's email the Worker passes on each request (`identity.Scope`).

`docs/identity.md` ("Profile") is the specification; the shapes below are the
contract `eesti/api/profile.py` and `eesti/web/js/profile.js` use.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

from .evidence import Event, Stores, applies

#: The name the learner chose.
PROFILE_SET = "profile-set"
#: The first contact of a permanent learner: registration. Recorded once, when
#: a learner's restored log settles without one (`evidence.settle`).
JOINED = "joined"
#: Clears learning projections while preserving the account and its profile.
PROGRESS_RESET = "profile-progress-reset"
#: Replays learning history through a particular reset marker.
PROGRESS_RESTORED = "profile-progress-restored"

#: Longest name accepted, after trimming.
NAME_MAX = 60


def clean_name(raw: str | None) -> str | None:
    """The name as stored: trimmed, inner whitespace collapsed; None when empty.

    Raises ValueError (Russian message) when it is longer than `NAME_MAX`.
    """
    name = " ".join((raw or "").split())
    if not name:
        return None
    if len(name) > NAME_MAX:
        raise ValueError(f"Имя длиннее {NAME_MAX} символов.")
    return name


@applies(JOINED)
@applies(PROFILE_SET)
def _profile_set(stores: Stores, ev: Event) -> None:
    """Nothing to project: the name and the date are read back from the log.

    Registered so strict replay (`cli verify-backup`) accepts the event. Add
    `profile` to `evidence._register_all` so the registration always runs.
    """
    return None


@applies(PROGRESS_RESET)
def _apply_progress_reset(stores: Stores, ev: Event) -> None:
    """Clear every learner projection; replaying the marker repeats the reset."""
    from . import evidence

    for database, tables in evidence.PROJECTIONS.items():
        conn = stores[database]
        with conn:
            for table in tables:
                conn.execute(f"DELETE FROM {table}")  # noqa: S608 - fixed schema names


def reset_state(current_events: list[Event]) -> tuple[Event | None, Event | None]:
    """Return the latest effective reset and the latest reset still restorable.

    A restore event neutralizes one reset during replay and consumes all older
    restore points. A later reset creates a new restore point.
    """
    restored_ids = {
        ev.payload.get("reset_event_id") for ev in current_events
        if ev.type == PROGRESS_RESTORED
    }
    restored_through = max(
        (int(ev.payload.get("through_seq", 0)) for ev in current_events
         if ev.type == PROGRESS_RESTORED), default=0)
    resets = [ev for ev in current_events if ev.type == PROGRESS_RESET]
    effective = next((ev for ev in reversed(resets) if ev.id not in restored_ids), None)
    latest = resets[-1] if resets else None
    restorable = latest if latest and (latest.seq or 0) > restored_through else None
    return effective, restorable


class NoRestorableProgress(LookupError):
    """There is no unconsumed reset point for this account."""


def reset_progress() -> dict:
    """Clear learning state in every projection and append a replayable marker.

    The append-only evidence history is kept for recovery/export; the marker
    makes its earlier events inactive in all rebuilt projections and summaries.
    """
    from . import evidence

    event = evidence.record(PROGRESS_RESET, {})
    stores = Stores()
    try:
        evidence.apply(stores, event)
    finally:
        stores.close()
    return {"reset": True, "event_id": event.id}


def restore_progress() -> dict:
    """Restore the latest reset point, keeping any later learning events.

    A later reset replaces this restore point. Restoring it does not reactivate
    still older reset points.
    """
    from . import evidence

    with closing(evidence.connect()) as log:
        _, reset = reset_state(evidence.events(log))
        if reset is None:
            raise NoRestorableProgress("there is no progress reset to restore")
        event = evidence.record(PROGRESS_RESTORED, {
            "reset_event_id": reset.id,
            "through_seq": reset.seq,
        })
        evidence.rebuild(log, strict=True)
    return {"restored": True, "event_id": event.id,
            "reset_event_id": reset.id}


def set_name(name: str | None) -> Event:
    """Record the learner's chosen name (`profile-set`, payload `{"name": ...}`).

    None clears the name.
    """
    from . import evidence

    return evidence.record(PROFILE_SET, {"name": clean_name(name)})


def name(log: sqlite3.Connection) -> str | None:
    """The name from the latest `profile-set` event, or None.

    The latest event wins, including an event that clears the name.
    """
    row = log.execute(
        "SELECT payload FROM events WHERE type = ? ORDER BY seq DESC LIMIT 1",
        (PROFILE_SET,),
    ).fetchone()
    if row is None:
        return None
    import json

    return json.loads(row["payload"]).get("name")


def summary(*, log: sqlite3.Connection, progress: sqlite3.Connection,
            reviews: sqlite3.Connection, vocabulary: sqlite3.Connection,
            scope) -> dict:
    """Everything `GET /api/me` returns. Shape (all keys always present):

        {
          "scope": "owner" | "learner" | "guest",
          "sandbox": str | None,             # the guest sandbox; None otherwise
          "name": str | None,
          "email": str | None,               # the account email; None for a guest
          "since": ISO timestamp | None,     # `joined`, else the first event
                                             # that is not `backfill`
          "last_active": ISO timestamp | None,   # latest practice event
          "active_days_28": int,             # days with practice, last 28
          "level": {
            "current": "A1" | "A2" | "B1" | None,  # level of `progress.resume`
            "goal": {...} | None,            # `exam.goal(...).to_dict()`
            "checkpoints": ["A1", ...],      # `checkpoint.passed_levels`
          },
          "milestones": {"A1": [...], "A2": [...], "B1": [...]},  # milestones.for_level
          "totals": {"attempts": int, "mastered": int, "topics": int,
                     "review_cards": int, "known_words": int},
          "rhythm": [...],                   # learner.daily_activity, as /api/status
          "restore_available": bool,
          "restore_at": ISO timestamp | None, # most recent available reset point
        }

    """
    from . import (checkpoint, config, exam, learner, milestones,
                   progress as progress_module, vocab)
    from .evidence import events
    from .curriculum import TOPICS, by_id

    current_topic = progress_module.resume(progress)
    current_level = by_id(current_topic).level if current_topic else None
    selected_goal = exam.goal(progress)
    current_events = events(log)

    joined = next((ev for ev in current_events if ev.type == JOINED), None)
    first = next((ev for ev in current_events if ev.type != "backfill"), None)
    since = joined or first
    reset, restorable_reset = reset_state(current_events)
    practice = [ev for ev in current_events
                if ev.type in learner.PRACTICE_EVENTS
                and (reset is None or ev.seq > reset.seq)]
    rhythm = learner.daily_activity(log, after_seq=reset.seq if reset else 0)
    active_days = sum(day["n"] > 0 for day in rhythm[-28:])
    last_active = max(practice, key=lambda ev: (ev.ts, ev.seq or 0)).ts if practice else None

    generator_topics = {topic.id for topic in TOPICS if topic.generator}
    attempts = progress.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    mastered = len(progress_module.mastered(progress) & generator_topics)
    review_cards = reviews.execute("SELECT COUNT(*) FROM review_items").fetchone()[0]
    known_words = vocabulary.execute(
        "SELECT COUNT(*) FROM vocab_status WHERE status IN (?,?)",
        (vocab.KNOWN, vocab.WELL_KNOWN),
    ).fetchone()[0]
    milestones_by_level = {
        level: milestones.for_level(progress, level) for level in config.LEVELS
    }

    return {
        "scope": scope.kind,
        "sandbox": scope.id if scope.is_guest else None,
        "name": name(log),
        "email": scope.email,
        "since": since.ts if since else None,
        "last_active": last_active,
        "active_days_28": active_days,
        "level": {
            "current": current_level,
            "goal": selected_goal.to_dict() if selected_goal else None,
            "checkpoints": sorted(checkpoint.passed_levels(progress)),
        },
        "milestones": milestones_by_level,
        "totals": {
            "attempts": attempts,
            "mastered": mastered,
            "topics": len(generator_topics),
            "review_cards": review_cards,
            "known_words": known_words,
        },
        "rhythm": rhythm,
        "restore_available": restorable_reset is not None,
        "restore_at": restorable_reset.ts if restorable_reset else None,
    }
