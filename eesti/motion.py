"""*käima* against *minema* (`kaima-minema`).

EKI's learner dictionary (PSV) separates them by what they take: *käima* —
*kus?*, *mida tegemas?* (*Suuremad lapsed käivad koolis*, *Käisin eelmisel
nädalal Riias*); *minema* — *kuhu?*, *mida tegema?* (*Naine läks poodi*).
So *käima* is being somewhere and coming back, or going there regularly, and
*minema* is setting off towards a place. Verb and place forms are Vabamorf's.
"""

from __future__ import annotations

import random

from .item import BLANK
from .morph import synthesize
from .patterns import PatternDrill

PLACES = ("kino", "teater", "pood", "raamatukogu", "ujula")


def _one(word: str, tag: str) -> str | None:
    found = synthesize(word, tag) or []
    return found[0] if len(found) == 1 else None


def _into(place: str) -> str | None:
    return _one(place, "adt") or _one(place, "sg ill")


#: verb, tag, frame, where-form, the other verb, why.
FRAMES = (
    ("käima", "sin", "Eile ma {} {w}.", "in", "minema",
     "Был и вернулся — **käima** + *kus?*: *käisin {w}* (как *Käisin eelmisel nädalal Riias*)."),
    ("käima", "vad", "Lapsed {} iga nädal {w}.", "in", "minema",
     "Регулярно ходят — **käima** + *kus?*: *käivad {w}* (как *lapsed käivad koolis*)."),
    ("minema", "n", "Homme ma {} {w}.", "ill", "käima",
     "Направляюсь куда — **minema** + *kuhu?*: *lähen {w}*."),
    ("minema", "s", "Naine {} {w}.", "ill", "käima",
     "Отправилась куда — **minema** + *kuhu?*: *läks {w}* (как *Naine läks poodi*)."),
    ("käima", "sin", "Eile ma {} ujumas.", "", "minema",
     "*käima* + **mas-vorm** (*mida tegemas?*): *käisin ujumas* — был и вернулся."),
    ("minema", "n", "Homme ma {} ujuma.", "", "käima",
     "*minema* + **ma-vorm** (*mida tegema?*): *lähen ujuma*."),
)


def drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    out: list[PatternDrill] = []
    for i in range(count * 4):
        if len(out) >= count:
            break
        verb, tag, frame, where, other, why = FRAMES[i % len(FRAMES)]
        place = rng.choice(PLACES)
        w = ""
        if where:
            w = _one(place, "sg in") if where == "in" else _into(place)
            if not w:
                continue
        answer, wrong = _one(verb, tag), _one(other, tag)
        if not answer or not wrong:
            continue
        item = PatternDrill(frame.format(BLANK, w=w), answer, wrong, "käima / minema",
                            "kus? või kuhu?", verb, why.format(w=w),
                            "kaima-minema", "A1")
        if all((item.prompt, item.answer) != (o.prompt, o.answer) for o in out):
            out.append(item)
    rng.shuffle(out)
    return out
