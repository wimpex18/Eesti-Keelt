"""The join between a grammar topic and something to read.

Split out of `library.py`, which had grown to 638 lines around two different
jobs: the shelf — what is in the library, what has been opened, for how long —
and this, which decides which texts *demonstrate* a grammar topic and writes
that into `topic_items`. They share a database and nothing else.

The join is earned, not asserted. A text is linked to a topic only if the
topic's own generator can cut a valid exercise out of it, so the claim has
already been checked by the machinery that refuses ambiguous cases. A
hand-typed label would have been faster and would have been a guess.

It is the piece that makes the app one tool rather than four: practice on its
own is a drill machine and a reading list on its own is a folder of texts. The
value is in "you keep missing the completed-object contrast — here is an ERR
episode that is *about* it."
"""

from __future__ import annotations

import sqlite3



# ---------------------------------------------------------------------------
# The join between a grammar topic and something to read
# ---------------------------------------------------------------------------
#
# This is the piece that makes the app one tool rather than four. Practice on
# its own is a drill machine; a reading list on its own is a folder of texts.
# The value is in "you keep missing the completed-object contrast — here is an
# ERR episode that is *about* it."
#
# The join is earned, not asserted. A text is linked to a topic only if the
# topic's own generator can cut a valid exercise out of it, which means the
# claim has already been checked by the machinery that refuses ambiguous cases.
# A hand-typed label would have been faster and would have been a guess.

#: Topics whose exercises come out of real sentences. Others -- conjugation,
#: question words, ordinals -- are generated from the word list, so no text
#: "demonstrates" them in a way worth pointing at.
LINKABLE = ("gen-stem", "osastav", "mitmus", "kohakaanded", "harvad-kaanded",
            "obj-case")


#: Below this a text merely contains the form in passing. The point is to offer
#: something a learner can read *for* the contrast, not anything that happens to
#: have a partitive in it.
MIN_HITS = 3



def _demonstrations(topic: str, sents: list[str], words) -> int:
    """How many sentences in this text exercise `topic`."""
    if topic == "obj-case":
        from .morph import has_distinct_object_cases, object_case_candidates

        return sum(
            1 for s in sents
            if any(has_distinct_object_cases(t.lemma)
                   for t in object_case_candidates(s))
        )

    from .cloze import case_clozes

    # `require_contrast` keeps this to sentences where the case is actually
    # doing work, which is the same bar the drill itself has to clear.
    return len(case_clozes(sents, topics=(topic,), words=words,
                           count=len(sents), seed=0))



#: Grammar terms a teacher used to label a lesson, mapped to the topic they name.
#:
#: This is a different kind of evidence from `_demonstrations`, and a stronger
#: one. That function asks "can a drill be cut from this text?"; this reads what
#: the person who made the lesson said it was about. Two thirds of the ERR
#: archive is audio with no transcript, so there is nothing to analyse — but
#: every episode carries a one-line label, and lessons 22 and 23 of the second
#: course are *precisely* the completed and incomplete object contrast.
#:
#: Estonian terms are matched because they are unambiguous. The two Russian
#: phrases are here because the object-case lessons name the contrast only in
#: Russian, and those are the two episodes that matter most.
LABEL_TOPICS: dict[str, tuple[str, ...]] = {
    "obj-case": ("падеж дополнения",),
    "osastav": ("osastav",),
    "gen-stem": ("omastav",),
    "kohakaanded": ("kohakäänded", "sisekohakäänded", "väliskohakäänded",
                    "sisseütlev", "alaleütlev", "seesütlev"),
    "rektsioon": ("rektsioon",),
    "taisminevik": ("täisminevik",),
    "enneminevik": ("enneminevik",),
    "lihtminevik": ("lihtminevik",),
    "mitmus": ("mitmuse",),
    "umbisikuline": ("umbisikuline", "безличная форма"),
    "kaskiv": ("повелительное наклонение", "käskiv"),
    "tingiv": ("условное наклонение", "tingiv"),
    "ma-da-inf": ("инфинитив", "infinitiiv"),
    "vordlusastmed": ("võrdlusastmed",),
}



def labelled_topics(text: str) -> list[str]:
    """Topics a lesson label names outright."""
    lowered = (text or "").casefold()
    return [topic for topic, terms in LABEL_TOPICS.items()
            if any(term in lowered for term in terms)]



def link_labelled(content: sqlite3.Connection) -> dict:
    """Link episodes to the topic their own label names.

    Runs alongside `link_topics` rather than instead of it: a transcript is
    evidence a text *uses* a form, a label is evidence a lesson *teaches* it,
    and the second is what you want when a topic keeps going wrong.

    Scored above any derived link, because a teacher saying "this lesson is
    about the object case in completed actions" outranks a program noticing
    three genitive objects went past.
    """
    LABEL_HITS = 999
    found = []
    for row in content.execute(
        "SELECT id, title, body, meta FROM items"
    ).fetchall():
        import json as _json

        try:
            meta = _json.loads(row["meta"] or "{}")
        except ValueError:
            meta = {}
        label = f"{meta.get('summary') or ''} {row['title'] or ''}"
        for topic in labelled_topics(label):
            found.append((topic, row["id"], LABEL_HITS))

    with content:
        content.executemany(
            "INSERT OR REPLACE INTO topic_items (topic, item_id, hits)"
            " VALUES (?,?,?)", found,
        )

    counts: dict[str, int] = {}
    for topic, _, _ in found:
        counts[topic] = counts.get(topic, 0) + 1
    return counts



def link_topics(content: sqlite3.Connection, words, topics=LINKABLE) -> dict:
    """Work out which texts demonstrate which topic, and store it.

    Slow on purpose and run rarely: it puts every sentence of the corpus through
    Vabamorf. The result lives in `content.db`, so pushing a harvest to the
    deployment carries the links with it and no container ever repeats this.
    """
    from .morph import split_sentences

    rows = content.execute(
        "SELECT id, body FROM items WHERE body <> ''"
    ).fetchall()

    found: list[tuple[str, str, int]] = []
    for row in rows:
        sents = [s.strip() for s in split_sentences(row["body"])
                 if 5 <= len(s.split()) <= 25]
        if not sents:
            continue
        for topic in topics:
            hits = _demonstrations(topic, sents, words)
            if hits >= MIN_HITS:
                found.append((topic, row["id"], hits))

    with content:
        content.execute("DELETE FROM topic_items")
        content.executemany(
            "INSERT OR REPLACE INTO topic_items (topic, item_id, hits)"
            " VALUES (?,?,?)", found,
        )

    counts: dict[str, int] = {}
    for topic, _, _ in found:
        counts[topic] = counts.get(topic, 0) + 1
    return counts



def related(
    content: sqlite3.Connection,
    topic: str,
    limit: int = 3,
    public_only: bool = False,
) -> list[dict]:
    """Texts worth reading for one topic, strongest first.

    `public_only` is honoured here for the same reason it exists everywhere
    else: most of this corpus is owner-only by licence, and a follow-up
    suggestion is still a way of serving it.
    """
    sql = """SELECT i.id, i.title, i.level, i.skill, i.audio_url,
                    s.name AS source_name, s.licence, t.hits
             FROM topic_items t
             JOIN items i ON i.id = t.item_id
             JOIN sources s ON s.id = i.source_id
             WHERE t.topic = ?"""
    if public_only:
        sql += " AND s.redistributable = 1"
    sql += " ORDER BY t.hits DESC, i.id LIMIT ?"
    return [dict(r) for r in content.execute(sql, (topic, limit)).fetchall()]
