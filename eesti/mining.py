"""Turning encounters into scheduled practice.

Two entry points, both feeding the same FSRS queue:

  a drill answered wrong   ->  the item that caught you out
  a word clicked in a text ->  the grammar pattern behind it, with the sentence

The second is the LingQ/Migaku move with one change. Those tools build a
*vocabulary* card, because a general tool cannot know why a word was hard. Here,
Vabamorf can say `raamatut` is the partitive of `raamat` and that the genitive
would be `raamatu` — so the card that gets queued is the object-case contrast in
the sentence you actually met, not a translation to memorise.

Words with nothing to teach are refused rather than queued. If a noun's genitive
and partitive are identical there is no contrast to drill, and a card that cannot
be got wrong wastes review time — the scarcest thing in spaced repetition.
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
        return MineResult(False, f"«{word}» ei ole sõnastikus")

    analyses = found["analyses"]
    # Prefer a reading that actually carries an object-case contrast.
    best = next(
        (a for a in analyses if a.get("object_case_contrast")), analyses[0]
    )
    lemma = best["lemma"]

    if not best.get("object_case_contrast"):
        return MineResult(
            False,
            f"«{lemma}»: omastav ja osastav on samad — pole midagi harjutada",
        )

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
