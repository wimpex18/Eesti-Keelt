"""Blocked practice becomes interleaved review.

Interleaving wins on long-term accuracy but is too hard for novices before the
rules are known, so the schedule is a sequence:

    new topic  ->  BLOCKED drills until the mastery gate  ->  INTERLEAVED review

Blocked is the generator filtered to one topic; interleaved is the FSRS queue.

- **On failure**, an item enters the queue already graded wrong, so FSRS brings
  it back soon (every generator).
- **On mastery**, a small sample of the topic's items joins the queue.

`review.add` keys on `(kind, lemma, tag)` and keeps existing schedules, so
re-adding is safe and the queue holds one item per (word, form).
"""

from __future__ import annotations

import sqlite3

from . import review

# How many of a mastered topic's items join the review queue. Small on purpose:
# a topic can generate hundreds, and a queue that spikes every time something is
# passed is a queue the learner stops opening.
SEED_ITEMS = 6


def _identity(item) -> tuple[str, str]:
    """(lemma, tag) for an item, stable across regenerations. Question-word items use
    the answer, since they have no lemma. The sub-rule wins over the label where an
    item has one (`obj-case`: negation, completed, ongoing): that is what the
    learner is getting wrong, and the page blanks the label on choice topics.
    """
    lemma = getattr(item, "lemma", "") or item.answer
    tag = getattr(item, "rule", "") or getattr(item, "label", None) or ""
    return lemma, tag


def queue_failed(conn: sqlite3.Connection, item) -> str:
    """Put a missed item into the queue, already marked missed, so it returns soon."""
    key = review.add(
        conn,
        kind=item.topic,
        lemma=_identity(item)[0],
        tag=_identity(item)[1],
        prompt=item.prompt,
        answer=item.answer,
        distractor=getattr(item, "distractor", None),
        why_ru=getattr(item, "why_ru", None),
        source="practice",
    )
    review.grade(conn, key, "again")
    return key


def review_correct(conn: sqlite3.Connection, item, latency_ms: int | None = None) -> str | None:
    """A correct answer to an item whose card is due is that card's review.

    Rated by code (`review.auto_rating`). A card not yet due is left alone: FSRS
    schedules the next look, and answering early is not a review of it.
    """
    from datetime import datetime, timezone

    lemma, tag = _identity(item)
    key = review.item_id(item.topic, lemma, tag)
    row = conn.execute("SELECT due FROM review_items WHERE id = ?", (key,)).fetchone()
    if row is None or row["due"] > datetime.now(timezone.utc).isoformat():
        return None
    review.grade(conn, key, review.auto_rating(True, latency_ms), auto=True,
                 given=item.answer, latency_ms=latency_ms)
    return key


def seed_mastered(
    conn: sqlite3.Connection,
    topic: str,
    count: int = SEED_ITEMS,
    seed: int | None = None,
) -> list[str]:
    """Move a just-mastered topic into the interleaved pool; existing items keep their
    schedule.
    """
    from .practice import items_for

    try:
        items = items_for(topic, count=count, seed=seed)
    except ValueError:  # topic has no generator; nothing to hand off
        return []

    return [
        review.add(
            conn,
            kind=topic,
            lemma=_identity(item)[0],
            tag=_identity(item)[1],
            prompt=item.prompt,
            answer=item.answer,
            distractor=getattr(item, "distractor", None),
            why_ru=getattr(item, "why_ru", None),
            source="mastery",
        )
        for item in items
    ]


def pending_handoffs(progress: sqlite3.Connection, reviews: sqlite3.Connection) -> list[str]:
    """Mastered topics with nothing in the review queue yet, so none stays outside
    the review pool.
    """
    from .progress import mastered

    queued = {r[0] for r in reviews.execute("SELECT DISTINCT kind FROM review_items")}
    return sorted(mastered(progress) - queued)
