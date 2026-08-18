"""One entry point for "give me practice on this topic".

Five generators now exist, each with its own signature and its own database
needs — the word list, the harvested corpus, EKK's rection table. The learner
does not care which; they asked to practise the conditional. This maps a
curriculum topic to items and keeps the dispatch in one place, so a new
generator is registered once rather than wired into every caller.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import CACHE, LEVELS


def _content(path: str | Path | None = None) -> sqlite3.Connection:
    # Resolved at call time. A hardcoded default here is how the test suite
    # ended up reading the developer's own harvest without anyone noticing.
    from . import config

    conn = sqlite3.connect(path or config.CONTENT_DB)
    conn.row_factory = sqlite3.Row
    return conn


def items_for(
    topic: str,
    count: int = 10,
    levels: tuple[str, ...] = LEVELS,
    seed: int | None = None,
    content_db: str | Path | None = None,
) -> list:
    """Practice items for one curriculum topic, from whichever generator owns it.

    Raises rather than returning an empty list when a topic has no generator:
    "nothing to practise" and "the generator produced nothing today" are
    different problems, and silently returning [] hides the first as the second.
    """
    from .curriculum import by_id

    generator = by_id(topic).generator
    if generator is None:
        raise ValueError(
            f"{topic!r} has no generator — see step 2 of docs/curriculum-plan.md"
        )

    from .wordlist import connect as wordlist_connect

    words = wordlist_connect()

    if generator == "conjugation":
        from .conjugation import generate

        return generate(words, topics=(topic,), levels=levels, count=count, seed=seed)

    if generator == "patterns":
        from .patterns import comparison_drills, numeral_drills, question_drills

        if topic == "kusisonad":
            return question_drills(count=count, seed=seed)
        if topic == "vordlusastmed":
            return comparison_drills(words, levels, count, seed)
        return numeral_drills(words, levels, count, seed, topics=(topic,))

    if generator == "corpus_cloze":
        from .cloze import case_clozes, negation_clozes, sentences

        sents = sentences(_content(content_db))
        if topic == "obj-case":
            return negation_clozes(sents, words=words, count=count, seed=seed)
        return case_clozes(
            sents, topics=(topic,), words=words, count=count, seed=seed
        )

    if generator == "ekk_rection":
        from .cloze import rection_clozes
        from .rection import at_levels, fetch

        pool = at_levels(words, fetch(cache=CACHE / "ekk_su64.html"), levels)
        return rection_clozes(pool, words=words, count=count, seed=seed)

    if generator == "object_case":
        from .drills import generate as generate_objcase

        return generate_objcase(words, count=count, levels=levels, seed=seed)

    if generator == "verb_stems":
        from .drills import generate_verb_drills

        return generate_verb_drills(words, count=count, levels=levels, seed=seed)

    raise ValueError(f"unknown generator {generator!r} for topic {topic!r}")
