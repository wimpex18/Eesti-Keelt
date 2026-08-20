"""Comma before a subordinate clause — the one punctuation rule worth drilling.

`kirjavahemargid` was one of three topics the curriculum plan listed as needing
"sentence-level machinery rather than form generation", and the first attempt
here was to close it the way `sonajark` was closed: from attested learner
corrections. That failed on volume — of 1 000 (learner wrote, native corrected)
pairs, only **6** differ by punctuation alone. Six is not a drill.

But four of those six are the same mistake, and it is the most mechanical rule
in Estonian punctuation: a subordinate clause takes a comma in front of it.

    ✗ Arvan, et on palju kergem elada kui valdad eesti keelt.
    ✓ Arvan, et on palju kergem elada, kui valdad eesti keelt.

So this one is **generated**, which `wordorder.py` explicitly refuses to do —
and the difference is a measurement, not a preference. Across 1 349 native
texts, counting mid-sentence occurrences:

    sest   99.0 % preceded by a comma   (105 occurrences)
    et     95.9 %                       (637)
    nagu   63.9 %                       (36)
    kui    37.8 %                       (331)

`kui` and `nagu` are not rules — `kui` is also the comparative ("suurem kui")
and `nagu` is also a preposition. They are excluded. `et` and `sest` hold, and
inspecting every exception showed them to be systematic rather than random:

  * a coordinating conjunction immediately before (`ja et`, `ning et`,
    `või et`) — no comma, correct;
  * fixed collocations: `ilma et`, `nii et`, `sellepärast et`;
  * sentence-initial `Sest …`, which is a new sentence, not a clause.

Excluding those, the rule is categorical, so removing the comma produces
Estonian that is *provably* wrong — which is exactly the property V2 lacked and
the reason word order is drilled from attested pairs instead.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from .item import GradedItem

TAG = "kirjavahemargid"

#: Only the two that measured categorical. `kui` and `nagu` are deliberately
#: absent: at 38 % and 64 % they are not rules, and drilling them would teach a
#: learner to insert commas into correct Estonian.
CONJUNCTIONS = ("et", "sest")

#: A coordinating conjunction or a fixed collocation immediately before the
#: subordinator means no comma. Every exception found in the native sample was
#: one of these.
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
    """Where a drillable `, et` / `, sest` sits, if anywhere.

    Mid-sentence only, and never where the preceding word makes the comma
    wrong.
    """
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
    """Items from native sentences that already punctuate correctly.

    The learner's version is made by deleting the comma, which is why the
    measurement above had to come first: if the rule were a tendency, that
    deletion would sometimes produce correct Estonian and the drill would be
    teaching the opposite of the rule.
    """
    import random

    rng = random.Random(seed)
    pool = list(sentences)
    rng.shuffle(pool)

    out: list[CommaItem] = []
    for sentence in pool:
        sentence = sentence.strip()
        # One comma per item: a sentence with two would have two right answers
        # under a single deletion, and the learner could not tell which was
        # being asked about.
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
