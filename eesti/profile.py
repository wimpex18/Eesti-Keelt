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

from .evidence import Event, Stores, applies

#: The name the learner chose.
PROFILE_SET = "profile-set"
#: The first contact of a permanent learner: registration. Recorded once, when
#: a learner's restored log settles without one (`evidence.settle`).
JOINED = "joined"

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
    practice = [ev for ev in current_events if ev.type in learner.PRACTICE_EVENTS]
    rhythm = learner.daily_activity(log)
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
    }
