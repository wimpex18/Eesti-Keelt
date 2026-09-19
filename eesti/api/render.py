"""Turning ids, lemmas and topics into what a learner actually reads.

Shared by practice, review and the checkpoint, so no screen prints a database
key.
"""

from __future__ import annotations

import sqlite3

from .deps import content_db, db, gloss_db


#: Topics whose drill is the *choice* of form. Printing the form before the answer
#: would make that choice for the learner: `obj-case` asks omastav or osastav.
CHOICE_TOPICS = frozenset({"obj-case"})


def item_for_page(item) -> dict:
    """An item as the page receives it. For a choice topic the form moves from
    `label` (shown under the blank) to `form_after` (shown with the verdict); `hint`,
    which the page sends back as the item's identity, is untouched."""
    shown = item.to_dict()
    if shown.get("topic") in CHOICE_TOPICS:
        shown["form_after"], shown["label"] = shown["label"], ""
    return shown


def _topic_reference(meta) -> dict | None:
    """The handbook link for a topic, by error tag or by topic id (same fallback as
    `GradedItem.reference`).
    """
    from ..grammar import describe as describe_rule

    if meta.tag:
        found = describe_rule(meta.tag)
        if found.get("known"):
            return found
    found = describe_rule(meta.id)
    return found if found.get("known") else None


def _topic_name(kind: str) -> str:
    """A curriculum id turned into words a learner recognises."""
    from ..curriculum import by_id

    try:
        return by_id(kind).et
    except KeyError:
        # `vocab`, or an id queued before a rename: the raw string beats a blank.
        return kind


def _glosses_for(lemmas: list[str]) -> dict[str, list[str]]:
    """Russian for whatever is known locally, in `meaning.py`'s order. Never fetches."""
    from ..meaning import russian_many

    try:
        return russian_many(db(), gloss_db(), lemmas)
    except sqlite3.Error:
        return {}


def reading_for(topic: str, limit: int = 3) -> list[dict]:
    """Texts that demonstrate a topic, or nothing if the corpus is unharvested."""
    from ..topiclinks import related

    try:
        return related(content_db(), topic, limit=limit)
    except sqlite3.Error:
        # An older content.db without the link table: return an empty reading list.
        return []
