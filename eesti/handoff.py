"""Blocked practice becomes interleaved review.

Step 5 of the curriculum plan, and the point where the two halves of this app
finally meet: `progress.py` decides when a topic has been learned, `review.py`
decides when it needs seeing again, and until now nothing connected them.

## Why this sequence and not a preference

The research is not "interleaving beats blocking". It is more specific and more
useful than that: interleaved practice wins on **long-term** accuracy, but
**interleaving alone is an undesirable difficulty for novices** — mixing rules
before any of them is understood makes all of them harder. Blocked practice in
the early phase is what builds the declarative knowledge that interleaving later
consolidates.

So the schedule is a sequence, not a choice:

    new topic  ->  BLOCKED drills until the mastery gate  ->  INTERLEAVED review

and both halves already existed. Blocked is the drill generator filtered to one
topic; interleaved is the FSRS queue, which mixes whatever is due by
construction. This module is the arrow between them.

## Two arrows, actually

**On failure**, an item goes into the queue *already graded wrong*, so FSRS
schedules it soon rather than treating it as fresh material. `mining.py` did this
for object-case and verb-form drills; here it works for every generator, which
is what six generators later it should.

**On mastery**, a sample of the topic's items joins the queue. Not all of them —
a topic can generate hundreds, and burying the queue under one newly-passed
topic is how a review backlog becomes something the learner stops opening. A
handful is enough for FSRS to track whether the topic is holding.

## Identity, and why re-adding is safe

`review.add` keys on `(kind, lemma, tag)` and keeps the schedule of anything it
already has. That is the behaviour we want here: passing a topic twice, or
meeting the same word in a later text, must not reset the memory model built for
it. It also means the queue holds one item per (word, form) rather than one per
sentence the word appeared in, which is the right grain — what is being reviewed
is the form, not the sentence.
"""

from __future__ import annotations

import sqlite3

from . import review

# How many of a mastered topic's items join the review queue. Small on purpose:
# a topic can generate hundreds, and a queue that spikes every time something is
# passed is a queue the learner stops opening.
SEED_ITEMS = 6


def _identity(item) -> tuple[str, str]:
    """(lemma, tag) for an item, stable across regenerations of the same drill.

    Question-word items carry no lemma — the word *is* the answer — so the answer
    stands in. Without that, all twelve would collapse onto one queue entry.
    """
    lemma = getattr(item, "lemma", "") or item.answer
    tag = getattr(item, "label", None) or getattr(item, "rule", "") or ""
    return lemma, tag


def queue_failed(conn: sqlite3.Connection, item) -> str:
    """Put a missed item into the queue, already marked missed.

    Adding and grading in one step is the whole trick: the item enters knowing it
    was wrong, so it comes back soon instead of being scheduled as new material.
    """
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


def seed_mastered(
    conn: sqlite3.Connection,
    topic: str,
    count: int = SEED_ITEMS,
    seed: int | None = None,
) -> list[str]:
    """Move a just-mastered topic from blocked practice into the interleaved pool.

    Anything already queued keeps its schedule, so calling this twice on the same
    topic is harmless.
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
    """Mastered topics with nothing in the review queue yet.

    The handoff normally happens the moment a topic is passed. This catches the
    ones that were mastered before this module existed, or passed in a session
    that ended before the queue was written — so a topic cannot silently sit
    outside the review pool forever.
    """
    from .progress import mastered

    queued = {r[0] for r in reviews.execute("SELECT DISTINCT kind FROM review_items")}
    return sorted(mastered(progress) - queued)
