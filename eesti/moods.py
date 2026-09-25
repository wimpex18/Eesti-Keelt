"""The indirect mood (`kaudne`): what someone else says, passed on.

EKI's learner grammar tables (PSV): the indirect mood shows that the
information comes from a third party and the speaker only passes it on. Present
`vat` (*lubavat, laulvat, tulevat*), past `olevat` + nud, negative `ei` + vat.
EKK M 74 also gives *Mari olla väga jutukas* with the da-infinitive. Every form
here is synthesised by Vabamorf.
"""

from __future__ import annotations

import random

from .item import BLANK
from .morph import synthesize
from .patterns import PatternDrill

#: verb, tense, frame, Russian for what is reported, the plain indicative tag.
FRAMES = (
    ("sadama", "present", "Homme {} vihma.", "говорят, завтра будет дождь", "b"),
    ("olema", "present", "Ta {} haige.", "говорят, он болен", "b"),
    ("tulema", "present", "Poodi {} uus müüja.", "говорят, в магазин придёт новый продавец", "b"),
    ("elama", "present", "Nad {} nüüd Tartus.", "говорят, они теперь живут в Тарту", "vad"),
    ("kolima", "past", "Naabrid {} Tartusse.", "говорят, соседи переехали в Тарту", "sid"),
    ("ostma", "past", "Mari {} uue auto.", "говорят, Мари купила новую машину", "s"),
    ("lõpetama", "past", "Ta {} kooli.", "говорят, он окончил школу", "s"),
)


def _one(verb: str, tag: str) -> str | None:
    found = synthesize(verb, tag) or []
    return found[0] if found else None


def drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    frames = list(FRAMES)
    rng.shuffle(frames)
    out: list[PatternDrill] = []
    for verb, tense, frame, ru, plain_tag in frames[:count]:
        if tense == "present":
            answer = _one(verb, "vat")
            why = f"Пересказ с чужих слов, настоящее — **vat**: *{answer}*."
        else:
            nud = _one(verb, "nud")
            answer = f"olevat {nud}" if nud else None
            why = f"Пересказ, прошедшее — **olevat + nud**: *{answer}*."
        plain = _one(verb, plain_tag)
        if not answer or not plain:
            continue
        out.append(PatternDrill(frame.format(BLANK), answer, plain, verb,
                                "kaudne kõneviis", tense, why, "kaudne", "B1",
                                answer_ru=(ru,)))
    return out
