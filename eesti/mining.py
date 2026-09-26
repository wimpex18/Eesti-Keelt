"""Turning a word met while reading into scheduled practice.

Like LingQ/Migaku, but the card is **grammar**: Vabamorf knows `raamatut` is the
partitive of `raamat`, so the queued card is the object-case contrast in the
sentence the learner met.

Words with no case contrast (identical genitive and partitive, about a third of
A1–B1 words) get a **meaning** card (`kind="vocab"`) instead — but only when a
Russian gloss is already in the local store: a card with no meaning cannot be
graded, and a live fetch here would put a third party in the click path.
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


def from_reading(
    conn: sqlite3.Connection,
    word: str,
    context: str | None = None,
) -> MineResult:
    """Queue the grammar pattern behind a word met while reading; returns a refusal
    with a reason when there is nothing to teach.
    """
    from .lookup import lookup

    found = lookup(word, context)
    if not found.get("found"):
        return MineResult(False, f"«{word}» — такого слова в словаре нет")

    analyses = found["analyses"]
    # The reading the sentence uses (`mulle` in *Anna mulle* is `mina`, not the
    # bubble); without one, a reading that carries an object-case contrast.
    best = next((a for a in analyses if a.get("in_context")), None) or next(
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
    """A card for what a word means, when there is no case contrast to drill. Reads
    local tables only, in `meaning.py`'s order; the live lookup belongs to the word
    card.
    """
    from . import config, gloss, wordlist
    from .meaning import russian as russian_for

    analysis = analysis or {}

    with gloss.connect(config.VOCAB_DB) as g:
        known = gloss.stored(g, lemma)

    words = wordlist.connect()
    try:
        russian, _ = russian_for(words, lemma, known.russian if known else ())
    finally:
        words.close()
    if not russian:
        # Two different absences: a noun whose forms coincide has no contrast; an adverb
        # or conjunction has no genitive or partitive at all. The refusal says which.
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
        # No `why_ru`: that slot is the Russian explanation, and the definition is
        # Estonian; the answer already explains a meaning card.
        why_ru=None,
        source="reading",
        context=context,
    )
    return MineResult(True, f"«{lemma}» lisatud kordamisse", item, "vocab")
