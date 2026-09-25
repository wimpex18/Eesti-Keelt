"""Conjunctions (`sidesonad`) and adverbs of place (`maarsonad`).

Neither inflects, so nothing is synthesised: the answer is the word itself.
Conjunction frames are EKK M 13's own examples, the blank where its
conjunction was. Adverbs of place come in threes, like the local cases (EKK M
7: *alla, all, alt*; EKI's learner grammar tables: *kuhu? kus? kust?*).
"""

from __future__ import annotations

import random

from .item import BLANK
from .patterns import PatternDrill

#: EKK M 13 sentence with the conjunction blanked, the conjunction, a wrong one,
#: the Russian, and what it is.
CONJUNCTIONS = (
    ("Tuleksin hea meelega, {} mul pole aega.", "aga", "et", "но", "противительный"),
    ("See on hea raamat, {} too teine on huvitavam.", "aga", "ja", "но", "противительный"),
    ("Ma tean, {} loota pole midagi.", "et", "kui", "что", "подчинительный"),
    ("Jüri on noorem {} Mari.", "kui", "nagu", "чем", "сравнение"),
    ("Söö, {} maitseb.", "kui", "et", "если", "условие"),
    ("Ole siin, {} ma tulen.", "kuni", "kui", "пока (не)", "время"),
    ("Ta vaatas mind {} ilmutust.", "nagu", "kui", "как", "сравнение"),
    ("Alguses lõi Jumal taeva {} maa.", "ja", "või", "и", "соединительный"),
    ("Nad peavad valima kas ühe {} teise võimaluse.", "või", "ja", "или", "разделительный"),
)

#: kuhu?, kus?, kust? and the Russian for each.
PLACE_SERIES = (
    (("koju", "домой"), ("kodus", "дома"), ("kodust", "из дома")),
    (("välja", "наружу"), ("väljas", "на улице, снаружи"), ("väljast", "с улицы, снаружи")),
    (("üles", "наверх"), ("üleval", "наверху"), ("ülevalt", "сверху")),
    (("alla", "вниз"), ("all", "внизу"), ("alt", "снизу")),
)
PLACE_FRAMES = (
    ("kuhu?", "Ma lähen {}.", 0),
    ("kus?", "Ma olen praegu {}.", 1),
    ("kust?", "Ta tuli just {}.", 2),
)


def conjunction_drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    rows = list(CONJUNCTIONS)
    rng.shuffle(rows)
    return [PatternDrill(frame.format(BLANK), answer, wrong, "", "sidesõna", kind,
                         f"«{ru}» — **{answer}** ({kind}): *{frame.format(answer)}*"
                         + (" Запятая — перед союзом." if ", {}" in frame else ""),
                         "sidesonad", "A1", answer_ru=(ru,))
            for frame, answer, wrong, ru, kind in rows[:count]]


def adverb_drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    out: list[PatternDrill] = []
    pairs = [(s, f) for s in PLACE_SERIES for f in PLACE_FRAMES]
    rng.shuffle(pairs)
    for series, (question, frame, i) in pairs[:count]:
        answer, ru = series[i]
        wrong = series[(i + 1) % 3][0]
        out.append(PatternDrill(
            frame.format(BLANK), answer, wrong, "", question, "koht",
            f"{question} — **{answer}**; ряд *{', '.join(w for w, _ in series)}* "
            "повторяет местные падежи: куда, где, откуда.",
            "maarsonad", "A1", answer_ru=(ru,)))
    return out
