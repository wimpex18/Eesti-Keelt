"""Comma before a subordinate clause — the one punctuation rule worth drilling.

Generated, because in native text the rule is categorical for `et` and `sest`:

    sest   99.0 % preceded by a comma
    et     95.9 %
    nagu   63.9 %   (also a preposition — excluded)
    kui    37.8 %   (also comparative "suurem kui" — excluded)

The exceptions are systematic and excluded: a coordinating conjunction before
(`ja et`, `ning et`, `või et`), fixed collocations (`ilma et`, `nii et`,
`sellepärast et`), and sentence-initial `Sest`. With those out, deleting the
comma produces Estonian that is provably wrong.

    ✗ Arvan, et on palju kergem elada kui valdad eesti keelt.
    ✓ Arvan, et on palju kergem elada, kui valdad eesti keelt.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from .item import GradedItem

#: Only the two subordinators that are categorical; `kui` and `nagu` are not rules.
CONJUNCTIONS = ("et", "sest")

#: A coordinating conjunction or fixed collocation immediately before the
#: subordinator means no comma.
NO_COMMA_AFTER = frozenset({
    "ja", "ning", "või", "ega",            # coordinating
    "ilma", "nii", "sellepärast", "selleks", "juhul", "eeldusel",
})

#: Russian, like every explanation the learner acts on.
WHY = (
    "**Запятая перед придаточным.** В эстонском придаточное предложение "
    "отделяется запятой: «Arvan**,** et see on õige», «Ta jäi koju**,** sest "
    "ta oli haige». Запятая ставится перед союзом, а не после него. "
    "Исключения — когда перед союзом стоит сочинительный союз (*ja et*, "
    "*ning et*) или устойчивое сочетание (*ilma et*, *nii et*)."
)


@dataclass(frozen=True)
class CommaItem(GradedItem):
    """One native sentence, offered with and without its comma."""

    prompt: str
    answer: str
    distractor: str
    lemma: str = ""
    topic: str = "kirjavahemargid"
    conjunction: str = "et"
    why_ru: str = WHY
    choices: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"koma enne «{self.conjunction}»"

    @property
    def hint(self) -> str:
        return self.label


def _spans(sentence: str) -> list[tuple[int, str]]:
    """Where a drillable `, et` / `, sest` sits mid-sentence, if anywhere."""
    out: list[tuple[int, str]] = []
    for word in CONJUNCTIONS:
        for m in re.finditer(rf",\s+{word}\s", sentence):
            before = sentence[: m.start()].split()
            if not before:
                continue                      # nothing in front: not a clause
            if before[-1].lower().strip(",") in NO_COMMA_AFTER:
                continue
            out.append((m.start(), word))
    return out


def from_sentences(sentences: list[str], count: int = 10,
                   seed: int | None = None) -> list[CommaItem]:
    """Items from native sentences that already punctuate correctly; the learner's
    version deletes the comma.
    """
    import random

    rng = random.Random(seed)
    pool = list(sentences)
    rng.shuffle(pool)

    out: list[CommaItem] = []
    for sentence in pool:
        sentence = sentence.strip()
        # One comma per item, so a single deletion has one right answer.
        found = _spans(sentence)
        if len(found) != 1:
            continue
        at, word = found[0]
        wrong = sentence[:at] + sentence[at + 1:]
        choices = [sentence, wrong]
        rng.shuffle(choices)
        out.append(CommaItem(
            prompt="Kumb lause on õige?",
            answer=sentence,
            distractor=wrong,
            conjunction=word,
            choices=tuple(choices),
        ))
        if len(out) >= count:
            break
    return out


def generate(count: int = 10, seed: int | None = None,
             content: sqlite3.Connection | None = None) -> list[CommaItem]:
    """Practice items for `kirjavahemargid`, from the harvested corpus."""
    if content is None:
        return []
    from .cloze import sentences

    # Long enough to hold a subordinate clause, short enough to read at a
    # glance in a two-way choice.
    pool = sentences(content, min_words=6, max_words=22)
    return from_sentences(pool, count=count, seed=seed)
