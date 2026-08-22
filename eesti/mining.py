"""Turning encounters into scheduled practice.

Two entry points, both feeding the same FSRS queue:

  a drill answered wrong   ->  the item that caught you out
  a word clicked in a text ->  the grammar pattern behind it, with the sentence

The second is the LingQ/Migaku move with one change. Those tools build a
*vocabulary* card, because a general tool cannot know why a word was hard. Here,
Vabamorf can say `raamatut` is the partitive of `raamat` and that the genitive
would be `raamatu` — so the card that gets queued is the object-case contrast in
the sentence you actually met, not a translation to memorise.

Words with no *grammar* to teach still have a meaning. If a noun's genitive and
partitive are identical there is no contrast to drill — a card that cannot be got
wrong wastes review time, the scarcest thing in spaced repetition — so those used
to be refused outright, with a message telling the learner there was nothing to
practise about a word they had just said they did not know.

That is 31.3 % of A1–B1 words (791 of 2 531, measured against `object_cases`):
A1 35.8 %, A2 34.9 %, B1 28.5 %. The reasoning above was right about the words it
was written for and was being applied to a third of the vocabulary it does not
describe. Those get a **meaning** card now — `kind="vocab"`, which the review
schema has documented since it was written and which nothing had ever produced.

The card is only queued when a Russian gloss is already in the local store. A
meaning card with no meaning on it cannot be graded, and fetching one here would
put a third party's server in the learner's click path, which `gloss.remember`
exists to keep out of.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from . import review


@dataclass(frozen=True)
class MineResult:
    queued: bool
    reason: str
    item_id: str | None = None
    kind: str | None = None


def from_failed_drill(
    conn: sqlite3.Connection,
    lemma: str,
    prompt: str,
    answer: str,
    distractor: str | None,
    rule: str,
    why_ru: str | None = None,
) -> MineResult:
    """Queue a drill the learner just got wrong, then record the failure.

    Adding and grading in one step is deliberate: an item enters the queue
    already knowing it was missed, so FSRS schedules it soon rather than treating
    it as fresh material.
    """
    kind = "verb-form" if rule == "verb-form" else "obj-case"
    item = review.add(
        conn, kind=kind, lemma=lemma, tag=rule, prompt=prompt, answer=answer,
        distractor=distractor, why_ru=why_ru, source="drill",
    )
    review.grade(conn, item, "again")
    return MineResult(True, "queued after a wrong answer", item, kind)


def from_reading(
    conn: sqlite3.Connection,
    word: str,
    context: str | None = None,
) -> MineResult:
    """Queue the grammar pattern behind a word met while reading.

    Returns a refusal rather than a card when there is nothing to teach, so the
    caller can say why instead of silently doing nothing.
    """
    from .lookup import lookup

    found = lookup(word)
    if not found.get("found"):
        return MineResult(False, f"«{word}» — такого слова в словаре нет")

    analyses = found["analyses"]
    # Prefer a reading that actually carries an object-case contrast.
    best = next(
        (a for a in analyses if a.get("object_case_contrast")), analyses[0]
    )
    lemma = best["lemma"]

    if not best.get("object_case_contrast"):
        return _meaning_card(conn, lemma, context, best)

    genitive, partitive = best["genitive"], best["partitive"]
    item = review.add(
        conn,
        kind="obj-case",
        lemma=lemma,
        tag="reading",
        prompt=f"«{lemma}» — sihitis: omastav või osastav?",
        answer=f"{genitive} / {partitive}",
        distractor=None,
        why_ru=(
            f"**omastav** *{genitive}* — действие завершено, объект целиком. "
            f"**osastav** *{partitive}* — процесс, часть или отрицание."
        ),
        source="reading",
        context=context,
    )
    return MineResult(True, f"«{lemma}» lisatud kordamisse", item, "obj-case")


def _meaning_card(
    conn: sqlite3.Connection, lemma: str, context: str | None,
    analysis: dict | None = None,
) -> MineResult:
    """A card for what a word means, when there is no case contrast to drill.

    Reads the local gloss store only. `gloss.remember` is the one call allowed
    to leave the machine and it belongs to the word card, where the learner is
    already waiting on it -- not here, where this runs behind a click that
    should feel instant.
    """
    from . import config, gloss

    analysis = analysis or {}

    with gloss.connect(config.VOCAB_DB) as g:
        known = gloss.stored(g, lemma)

    russian = list(known.russian) if known else []
    if not russian:
        # Two different absences, and saying the wrong one is worse than saying
        # nothing. A noun whose forms coincide has no contrast; an adverb or a
        # conjunction has no genitive or partitive *at all*, and telling the
        # learner that `kiiresti`'s omastav equals its osastav states something
        # untrue about a word that has neither.
        declines = bool(analysis.get("genitive") and analysis.get("partitive"))
        why = ("**omastav** и **osastav** совпадают"
               if declines else "это слово не склоняется")
        return MineResult(
            False,
            f"«{lemma}»: {why}, а перевод пока неизвестен. "
            f"Он подгрузится сам — попробуй ещё раз чуть позже.",
        )

    meaning = ", ".join(russian[:3])
    item = review.add(
        conn,
        kind="vocab",
        lemma=lemma,
        tag="meaning",
        prompt=f"«{lemma}» — mida see tähendab?",
        answer=meaning,
        distractor=None,
        # Nothing. `why_ru` is the Russian explanation slot and renders as
        # such; Sõnaveeb's `definition` is **Estonian**, so putting it here
        # printed `filmide näitamise asutus…` under a heading promising
        # Russian. The answer is already the explanation on a meaning card.
        why_ru=None,
        source="reading",
        context=context,
    )
    return MineResult(True, f"«{lemma}» lisatud kordamisse", item, "vocab")
