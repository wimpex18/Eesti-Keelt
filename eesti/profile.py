"""The learner's profile: who they are and how far they have come (ADR-0006).

Derived, like everything else, from the evidence log and the projections; the
only thing stored is the name, as a `profile-set` event. There is no profile
table and no second persistence source. Email is not stored at all: it is the
Access identity the Worker passes on each request (`identity.Scope`).

SKELETON. `docs/identity.md` ("Profile") is the specification; the shapes
below are the contract `eesti/api/profile.py` and `eesti/web/js/profile.js`
are written against. Replace every `NotImplementedError`.
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

    TODO(Luna): `clean_name`, then `evidence.record(PROFILE_SET, {"name": ...})`.
    None clears the name.
    """
    raise NotImplementedError


def name(log: sqlite3.Connection) -> str | None:
    """The name from the latest `profile-set` event, or None.

    TODO(Luna): newest `profile-set` by `seq`.
    """
    raise NotImplementedError


def summary(*, log: sqlite3.Connection, progress: sqlite3.Connection,
            reviews: sqlite3.Connection, vocabulary: sqlite3.Connection,
            scope) -> dict:
    """Everything `GET /api/me` returns. Shape (all keys always present):

        {
          "scope": "owner" | "learner" | "guest",
          "sandbox": str | None,             # the guest sandbox; None otherwise
          "name": str | None,
          "email": str | None,               # the Access email; None for a service token
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

    TODO(Luna): compose from the existing functions named above; add no new
    measure, streak or score.
    """
    raise NotImplementedError
