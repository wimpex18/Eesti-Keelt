"""The other forms of the ma-infinitive and the des-form (`ma-vormid`).

EKK M 76: `ma` is where the action goes (*Läksime sööma*), `mas` where it is
happening (*Olime marju korjamas*), `mast` where it comes from (*Tulime
söömast*; *Mari lakkas söömast*), `mata` the action not done (*Jätsin toa
koristamata*). EKK M 80: the des-form is an action happening alongside another
and describing it (*Lauldes ja hõisates tormasid poisid majast välja*).

Frames follow those examples; every answer is synthesised by Vabamorf.
"""

from __future__ import annotations

import random

from .item import BLANK
from .morph import synthesize
from .patterns import PatternDrill

#: Activities one goes to, is at, and comes back from.
ACTIVITIES = ("ujuma", "jalutama", "tantsima", "sööma", "magama", "suusatama",
              "jooksma")
#: What one can leave undone, with the object in the form the frame needs.
UNDONE = (("toa", "koristama"), ("raamatu", "lugema"), ("kirja", "kirjutama"),
          ("töö", "tegema"), ("nõud", "pesema"))
#: Ways of coming into a room.
MANNER = ("naeratama", "laulma", "nutma", "vilistama", "jooksma")
#: What one stops doing (`lakkama` + mast).
STOPPED = ("nutma", "laulma", "naeratama")

KINDS = (
    # tag, question, frame (with {obj} where needed), verbs, the wrong sibling, why
    ("ma", "kuhu?", "Ma lähen {}.", ACTIVITIES, "mas",
     "Куда идут делать — **ma-vorm**: *{a}*."),
    ("mas", "kus?", "Lapsed on praegu {}.", ACTIVITIES, "ma",
     "Где заняты делом — **mas-vorm**: *{a}* (как *Olime marju korjamas*)."),
    ("mast", "kust?", "Ma tulin just {}.", ACTIVITIES, "mas",
     "Откуда вернулись — **mast-vorm**: *{a}* (как *Tulime söömast*)."),
    ("mast", "mida lakkas?", "Laps lakkas {}.", STOPPED, "ma",
     "*lakkama* + **mast-vorm**: *lakkas {a}* — перестал."),
    ("mata", "mida jättis?", "Ma jätsin {obj} {}.", UNDONE, "ma",
     "Несделанное — **mata-vorm**: *jätsin {obj} {a}* (как *Jätsin toa koristamata*)."),
    ("des", "kuidas?", "Ta tuli tuppa {}.", MANNER, "mas",
     "Одновременное действие, которое описывает другое — **des-vorm**: *{a}* "
     "(русское деепричастие)."),
)


def _one(verb: str, tag: str) -> str | None:
    found = synthesize(verb, tag) or []
    return found[0] if found else None


def drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    out: list[PatternDrill] = []
    for i in range(count * 4):
        if len(out) >= count:
            break
        tag, question, frame, pool, sibling, why = KINDS[i % len(KINDS)]
        pick = rng.choice(pool)
        obj, verb = pick if isinstance(pick, tuple) else ("", pick)
        answer, wrong = _one(verb, tag), _one(verb, sibling)
        if not answer or not wrong or answer == wrong:
            continue
        prompt = frame.format(BLANK, obj=obj) if obj else frame.format(BLANK)
        item = PatternDrill(
            prompt, answer, wrong, verb, question, tag,
            why.format(a=answer, obj=obj), "ma-vormid", "A2")
        if all((item.prompt, item.answer) != (o.prompt, o.answer) for o in out):
            out.append(item)
    rng.shuffle(out)
    return out
