"""One entry point for "give me practice on this topic".

Five generators now exist, each with its own signature and its own database
needs — the word list, the harvested corpus, EKK's rection table. The learner
does not care which; they asked to practise the conditional. This maps a
curriculum topic to items and keeps the dispatch in one place, so a new
generator is registered once rather than wired into every caller.
"""

from __future__ import annotations

import random
import sqlite3
from pathlib import Path

from .config import LEVELS


def _content(path: str | Path | None = None) -> sqlite3.Connection:
    # Resolved at call time. A hardcoded default here is how the test suite
    # ended up reading the developer's own harvest without anyone noticing.
    from . import config

    conn = sqlite3.connect(path or config.CONTENT_DB)
    conn.row_factory = sqlite3.Row
    return conn


#: The three vocabulary slots a theme can narrow a drill by. `countable` is a
#: subset of `nouns`, kept apart because counting needs it.
THEME_SLOTS = ("nouns", "verbs", "countable")


def theme_slot(topic: str) -> str | None:
    """Which of a theme's word lists this topic is drilled over, or None.

    A theme picks *words*; it never changes what is being drilled. Some topics
    have no word to vary — question words, comparatives, ordinals, commas,
    word order and the rection table are closed classes or fixed inventories —
    and for those a theme is not "ignored", it is **inapplicable**.

    The distinction has to leave this module, because the page offers the
    theme as a control. It offered it on every topic, so choosing *Kodu ja
    elamine* on `küsisõnad` changed nothing at all: no error, no note, the same
    drills. That is this project's most-repeated bug wearing its sixth costume
    — a control with nothing behind it — and the only honest fix is for the
    page to be able to ask, before offering it, whether this topic can answer.

    This is also the single place the answer is decided. It used to be three
    variables computed up front and picked between at each branch, which is two
    places to keep in step; `items_for` now reads this and passes one `only`.
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
    # `object_case`, `verb_stems`, `ekk_rection`, `wordorder` and `punctuation`
    # all draw from a fixed inventory -- a stored rection table, attested
    # corrections, sentences chosen for their commas -- rather than picking a
    # lemma, so there is nothing for a theme to narrow.
    return None


def items_for(
    topic: str,
    count: int = 10,
    levels: tuple[str, ...] = LEVELS,
    seed: int | None = None,
    content_db: str | Path | None = None,
    theme: str | None = None,
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

    from .wordlist import available
    from .wordlist import connect as wordlist_connect

    # Asked before opening, because `wordlist_connect` *creates*: it makes the
    # file and applies the schema, so generating a drill against an unbuilt
    # deployment left a complete-looking, zero-row `data/eesti.db` behind. Every
    # caller that reaches here does so on a learner action -- `/api/practice`,
    # placement, the checkpoint, the handoff -- so this is the one that could
    # manufacture a phantom on the live app rather than only on the CLI.
    #
    # Raised, not returned empty: the route above turns ValueError into a 400
    # carrying this text, and "no items" would read as "this topic is broken"
    # rather than "nothing has been built here". Same shape and same reason as
    # the missing-generator raise a few lines up.
    if not available():
        raise ValueError(
            "no word list built — run `python -m eesti.cli fetch-data` and "
            "then `python -m eesti.cli build`"
        )

    words = wordlist_connect()

    # A theme narrows *which words* a topic is drilled over, without changing
    # what is being drilled. Some generators cannot honour it — question words
    # and ordinals are closed classes with no vocabulary to vary — and those
    # ignore it rather than returning nothing, because a lesson that silently
    # produces zero items is worse than one that is thematic in only half its
    # exercises.
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
            return question_drills(count=count, seed=seed)
        if topic == "vordlusastmed":
            return comparison_drills(words, levels, count, seed)
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
        # `levels` reaches the generator now. It was accepted here, threaded
        # this far and then dropped: `only` is None unless a theme is chosen,
        # so the default run of every corpus topic drilled whatever noun the
        # sentence happened to contain -- B2 `hooldustöö` inside an A1 topic.
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
        return _object_case(words, count, levels, seed, content_db)

    if generator == "verb_stems":
        from .drills import generate_verb_drills

        return generate_verb_drills(words, count=count, levels=levels, seed=seed)

    raise ValueError(f"unknown generator {generator!r} for topic {topic!r}")


#: How much of an object-case set comes from real Estonian rather than a frame.
#:
#: A third: enough that a learner meets the rule outside my twelve templates,
#: not so much that a thin corpus decides the size of the set.
CORPUS_SHARE = 3


def _object_case(
    words: sqlite3.Connection,
    count: int,
    levels: tuple[str, ...],
    seed: int | None,
    content_db: str | Path | None,
) -> list:
    """Template drills for `obj-case`, blended with authentic negation clozes.

    Negation is the one object-case rule a corpus sentence settles on its own —
    under it the partitive is exception-free, so no aspect judgement is needed
    and the genitive really is wrong. `cloze.negation_clozes` was written for
    exactly that, is tested, files its items under `obj-case`, and **reached
    nobody**: the branch that called it sat under `generator == "corpus_cloze"`,
    and `obj-case`'s generator is `object_case`, so `topic == "obj-case"` was
    never true there. A generator with no caller — this project's most-repeated
    bug, in another costume, and this time on the topic `docs/status.md` calls
    the documented #1 weakness.

    The corpus stays optional. A deployment without `content.db` — and the test
    suite's four short passages — yields no negation items, and the templates
    fill the whole set rather than the topic going short.
    """
    from .drills import generate as generate_objcase

    share = count // CORPUS_SHARE
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
        words, count=count - len(authentic), levels=levels, seed=seed)
    items += authentic
    # Interleaved rather than a block of corpus sentences after a block of
    # frames, which reads as two exercises stapled together.
    random.Random(seed).shuffle(items)
    return items
