"""Turning ids, lemmas and topics into what a learner actually reads.

Shared by practice, review and the checkpoint, and here rather than in any one
of them because a database key on screen is a bug even when it renders: the
review queue printed `obj-case` beside every card for as long as each screen
resolved ids for itself. Resolve them where the API answers.
"""

from __future__ import annotations

import sqlite3

from .deps import content_db, gloss_db


def _topic_reference(meta) -> dict | None:
    """The handbook link for a topic, by error tag or by topic id.

    Same fallback as `GradedItem.reference`, and here for the same reason: the
    empty-topic message promises a rule to read, and most topics have no error
    tag to find one by.
    """
    from ..grammar import describe as describe_rule

    if meta.tag:
        found = describe_rule(meta.tag)
        if found.get("known"):
            return found
    found = describe_rule(meta.id)
    return found if found.get("known") else None


def _topic_name(kind: str) -> str:
    """A curriculum id turned into words a learner recognises.

    `obj-case` and `kusisonad` are database keys. The path panel already
    resolves them -- `overview.py` does it for exactly this reason -- and the
    review queue was still printing the raw id beside every card.
    """
    from ..curriculum import by_id

    try:
        return by_id(kind).et
    except KeyError:
        # `vocab`, and anything queued before a topic was renamed. The raw
        # string is a worse label than a real name and a better one than blank.
        return kind


def _glosses_for(lemmas: list[str]) -> dict[str, list[str]]:
    """Russian for whatever is already known locally. Never fetches."""
    from .. import gloss

    try:
        found = gloss.stored_many(gloss_db(), lemmas)
    except sqlite3.Error:
        return {}
    return {k: list(g.russian) for k, g in found.items() if g.russian}


def reading_for(topic: str, limit: int = 3) -> list[dict]:
    """Texts that demonstrate a topic, or nothing if the corpus is unharvested."""
    from ..library import related

    try:
        return related(content_db(), topic, limit=limit)
    except sqlite3.Error:
        # An older content.db predates the link table. An empty reading list is
        # the right degradation -- the practice items are the lesson.
        return []
