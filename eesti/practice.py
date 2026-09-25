"""One entry point for "give me practice on this topic": maps a curriculum topic
to its generator, so a new generator is registered once.
"""

from __future__ import annotations

import random
import sqlite3
from pathlib import Path

from .config import LEVELS


def _content(path: str | Path | None = None) -> sqlite3.Connection:
    """The corpus, resolved at call time through `sources.connect`, which applies the
    schema (or returns an empty in-memory library) so corpus topics degrade to no
    items instead of failing when the corpus is absent.
    """
    from . import config
    from .sources import connect

    return connect(path or config.CONTENT_DB)


#: The three vocabulary slots a theme can narrow a drill by. `countable` is a
#: subset of `nouns`, kept apart because counting needs it.
THEME_SLOTS = ("nouns", "verbs", "countable")


def theme_slot(topic: str) -> str | None:
    """Which of a theme's word lists this topic is drilled over, or None.

    A theme picks words; it never changes what is drilled. Closed-class topics have
    no word to vary, so a theme is inapplicable there — and the page asks this
    before offering the control. `items_for` reads it and passes one `only`.
    """
    from .curriculum import by_id

    generator = by_id(topic).generator
    if generator == "conjugation":
        return "verbs"
    if generator == "forms":
        return "verbs" if topic == "eitus" else "nouns"
    if generator == "patterns":
        return "countable" if topic == "arvsonad" else None
    if generator == "corpus_cloze":
        return "nouns"
    # These generators draw from fixed inventories, not a lemma, so a theme has
    # nothing to narrow.
    return None


def items_for(
    topic: str,
    count: int = 10,
    levels: tuple[str, ...] = LEVELS,
    seed: int | None = None,
    content_db: str | Path | None = None,
    theme: str | None = None,
    rules: tuple[str, ...] | None = None,
) -> list:
    """Practice items for one curriculum topic, from whichever generator owns it.

    `rules` narrows `obj-case` to some of its sub-rules (`negation`, `completed`,
    `ongoing`); no other generator has sub-rules, so it is ignored elsewhere.

    Raises when a topic has no generator, so "nothing to practise" is not mistaken
    for "the generator produced nothing".
    """
    from .curriculum import by_id

    generator = by_id(topic).generator
    if generator is None:
        raise ValueError(
            f"{topic!r} has no generator — see docs/status.md"
        )

    from .wordlist import available
    from .wordlist import connect as wordlist_connect

    # Check the word list exists before opening: `wordlist_connect` creates the file.
    # Raised (a 400 with this text), so "nothing built" is not read as "topic broken".
    if not available():
        raise ValueError(
            "no word list built — run `python -m eesti.cli fetch-data` and "
            "then `python -m eesti.cli build`"
        )

    words = wordlist_connect()

    # A theme narrows which words are drilled; generators that cannot honour it
    # ignore it rather than returning nothing.
    only = None
    if theme is not None and (slot := theme_slot(topic)):
        from .themes import countable_nouns, lemmas_for

        if slot == "countable":
            # Counting needs a narrower list than reading does: "kaks suhkrut"
            # is not a sentence anyone says.
            only = frozenset(countable_nouns(words, theme, levels))
        else:
            only = frozenset(lemmas_for(
                words, theme, levels, pos="v" if slot == "verbs" else "s"))

    if generator == "conjugation":
        from .conjugation import generate

        return generate(words, topics=(topic,), levels=levels, count=count,
                        seed=seed, only=only)

    if generator == "patterns":
        from .patterns import comparison_drills, numeral_drills, question_drills

        if topic == "kusisonad":
            return question_drills(count=count, seed=seed, words=words)
        if topic == "vordlusastmed":
            return comparison_drills(words, levels, count, seed)
        if topic == "asesonad":
            from .pronouns import drills as pronoun_drills

            return pronoun_drills(count, seed)
        if topic == "kaassonad":
            from .postpositions import drills as postposition_drills

            return postposition_drills(count, seed)
        if topic == "kaima-minema":
            from .motion import drills as motion_drills

            return motion_drills(count, seed)
        if topic == "tuletus":
            from .wordbuilding import drills as derivation_drills

            return derivation_drills(words, count, seed)
        if topic == "ma-vormid":
            from .verbforms import drills

            return drills(count, seed)
        if topic in ("kellaaeg", "kuupaevad"):
            from .timedate import date_drills, time_drills

            make = time_drills if topic == "kellaaeg" else date_drills
            return make(count, seed)
        return numeral_drills(words, levels, count, seed, topics=(topic,),
                              only=only)

    if generator == "forms":
        from .forms import (agreement_drills, negation_drills,
                            principal_forms)

        if topic == "eitus":
            return negation_drills(words, levels=levels, count=count,
                                   seed=seed, only=only)
        if topic == "uhildumine":
            return agreement_drills(words, levels=levels, count=count,
                                    seed=seed, only=only)
        return principal_forms(words, levels=levels, count=count, seed=seed,
                               only=only)

    if generator == "punctuation":
        from .punctuation import generate as comma_items

        return comma_items(count=count, seed=seed, content=_content(content_db))

    if generator == "wordorder":
        from .wordorder import generate as wordorder_items

        # Reads the content store, where the pairs are ingested, so the items
        # reach a deployment the same way the reading library does.
        return wordorder_items(count=count, seed=seed,
                               content=_content(content_db))

    if generator == "corpus_cloze":
        from .cloze import case_clozes, sentences

        sents = sentences(_content(content_db))
        # Pass `levels` to the generator so corpus topics drill level-appropriate words.
        return case_clozes(
            sents, topics=(topic,), words=words, count=count, seed=seed,
            only=only, levels=levels,
        )

    if generator == "ekk_rection":
        from .cloze import rection_clozes
        from .rection import at_levels, load

        stored = load(words)
        if not stored:
            raise ValueError(
                "no rections stored — run `python -m eesti.cli rections` once. "
                "They are fetched deliberately, never during a lesson."
            )
        return rection_clozes(
            at_levels(words, stored, levels), words=words, count=count, seed=seed
        )

    if generator == "object_case":
        return _object_case(words, count, levels, seed, content_db, rules)

    if generator == "verb_stems":
        from .drills import generate_verb_drills

        return generate_verb_drills(words, count=count, levels=levels, seed=seed)

    raise ValueError(f"unknown generator {generator!r} for topic {topic!r}")


#: Share of an object-case set taken from real Estonian (negation clozes).
CORPUS_SHARE = 3


def _object_case(
    words: sqlite3.Connection,
    count: int,
    levels: tuple[str, ...],
    seed: int | None,
    content_db: str | Path | None,
    rules: tuple[str, ...] | None = None,
) -> list:
    """Template drills for `obj-case`, blended with authentic negation clozes.

    Negation is the one object-case rule a corpus sentence settles alone (the
    partitive is exception-free). Without `content.db` the templates fill the set.
    """
    from .drills import generate as generate_objcase

    # Corpus clozes are all negation, so they join only a set that includes it.
    share = count // CORPUS_SHARE if not rules or "negation" in rules else 0
    authentic: list = []
    if share:
        from .cloze import negation_clozes, sentences

        try:
            authentic = negation_clozes(
                sentences(_content(content_db)), words=words, count=share,
                seed=seed, levels=levels)
        except sqlite3.Error:
            # No content store, or one without the harvest. Not an outage of
            # this topic: it had none of these items yesterday either.
            authentic = []

    items = generate_objcase(
        words, count=count - len(authentic), levels=levels, seed=seed, rules=rules)
    items += authentic
    # Interleaved rather than a block of corpus sentences after a block of
    # frames, which reads as two exercises stapled together.
    random.Random(seed).shuffle(items)
    return items
