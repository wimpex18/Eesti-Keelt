"""Nouns from verbs (`tuletus`): the action with -mine, the doer with -ja.

EKK SM 21: -mine makes an action noun from any verb (*rääkima > rääkimine*),
also the names of activities (*laulmine, joonistamine*). EKK SM 22: -ja makes
the doer (*sööja, laulja, õpetaja*), attached to the ma-stem. A derived word is
drilled only when the word list has it, so no noun is invented.
"""

from __future__ import annotations

import random
import sqlite3

from .item import BLANK
from .morph import synthesize
from .patterns import PatternDrill

VERBS = ("laulma", "õpetama", "müüma", "ostma", "lugema", "kirjutama", "jooksma",
         "ujuma", "sööma", "töötama", "mängima", "tantsima", "suusatama",
         "jalutama", "joonistama")

FRAMES = (
    ("mine", "{} on tervislik.", ("jooksma", "ujuma", "tantsima", "suusatama", "jalutama"),
     "Действие как предмет — **-mine**: *{a}* (как *Jooksmine on tervislik*)."),
    ("mine", "Mulle meeldib {}.", VERBS,
     "Занятие как существительное — **-mine**: *meeldib {a}*."),
    ("ja", "Ta on hea {}.", ("laulma", "õpetama", "müüma", "lugema", "kirjutama",
                             "jooksma", "ujuma", "mängima", "tantsima"),
     "Тот, кто делает, — **-ja**: *{a}* (*laulma → laulja*, *õpetama → õpetaja*)."),
)


def derived(verb: str, suffix: str, words: sqlite3.Connection) -> str | None:
    """The -mine or -ja noun of a verb, only if the word list has it."""
    ma = (synthesize(verb, "ma") or [""])[0]
    if not ma.endswith("ma"):
        return None
    word = ma[:-2] + suffix
    found = words.execute("SELECT 1 FROM words WHERE word = ?", (word,)).fetchone()
    return word if found else None


def drills(words: sqlite3.Connection, count: int = 10,
           seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    out: list[PatternDrill] = []
    for i in range(count * 4):
        if len(out) >= count:
            break
        suffix, frame, pool, why = FRAMES[i % len(FRAMES)]
        verb = rng.choice(pool)
        answer = derived(verb, suffix, words)
        other = derived(verb, "ja" if suffix == "mine" else "mine", words)
        if not answer or not other:
            continue
        prompt = frame.format(BLANK)
        a = answer.capitalize() if prompt.startswith(BLANK) else answer
        item = PatternDrill(prompt, answer, other, verb, f"-{suffix}", suffix,
                            why.format(a=a), "tuletus", "A2")
        if all((item.prompt, item.answer) != (o.prompt, o.answer) for o in out):
            out.append(item)
    rng.shuffle(out)
    return out
