"""Pre- and postpositions (`kaassonad`), and the case each one takes.

EKK M 11: most are postpositions after `omastav` (*katuse all, maja ees, aia
ääres*); the few prepositions mostly take `osastav` (*enne koitu, keset teed,
piki randa*); a few take another case (*ilma emata*, *kuni metsani*, *tänu
sõbrale*); *pärast tööd* is time. Every noun form is synthesised by Vabamorf.
"""

from __future__ import annotations

import random

from .item import BLANK
from .morph import synthesize
from .patterns import PatternDrill

#: tag, frame, nouns, case name, why.
FRAMES = (
    ("sg g", "Kass on {} all.", ("laud", "tool", "voodi", "auto"), "omastav",
     "Послелог *all* — после **omastav**: *{a} all* (как *katuse all*)."),
    ("sg g", "Auto seisab {} ees.", ("maja", "uks", "pood"), "omastav",
     "Послелог *ees* — после **omastav**: *{a} ees* (как *maja ees*)."),
    ("sg g", "Me istume {} ääres.", ("laud", "aken", "meri"), "omastav",
     "Послелог *ääres* — после **omastav**: *{a} ääres* (как *aia ääres*)."),
    ("sg p", "Kohtume enne {}.", ("töö", "lõuna", "õhtu"), "osastav",
     "Предлог *enne* — с **osastav**: *enne {a}* (как *enne koitu*)."),
    ("sg p", "Ma helistan pärast {}.", ("töö", "lõuna", "koosolek"), "osastav",
     "*pärast* перед словом — время, с **osastav**: *pärast {a}* (как *pärast tööd*)."),
    ("sg p", "Auto seisis keset {}.", ("tee", "linn", "väljak"), "osastav",
     "Предлог *keset* — с **osastav**: *keset {a}* (как *keset teed*)."),
    ("sg ab", "Ta tuli ilma {}.", ("vihmavari", "müts", "raha"), "ilmaütlev",
     "*ilma* — с **ilmaütlev**: *ilma {a}* (как *ilma emata*)."),
    ("sg all", "Tänu {} leidsin töö.", ("sõber", "õde", "naaber"), "alaleütlev",
     "*tänu* — с **alaleütlev**: *tänu {a}* (как *tänu sõbrale*)."),
)


def drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    out: list[PatternDrill] = []
    for i in range(count * 4):
        if len(out) >= count:
            break
        tag, frame, nouns, case, why = FRAMES[i % len(FRAMES)]
        noun = rng.choice(nouns)
        forms = synthesize(noun, tag) or []
        if len(forms) != 1:
            continue          # an ambiguous form is no answer key
        answer = forms[0]
        wrong = (synthesize(noun, "sg p" if tag == "sg g" else "sg g") or [noun])[0]
        if wrong == answer:
            wrong = noun
        item = PatternDrill(frame.format(BLANK), answer, wrong, noun, case, "kaassona",
                            why.format(a=answer), "kaassonad", "A1")
        if all((item.prompt, item.answer) != (o.prompt, o.answer) for o in out):
            out.append(item)
    rng.shuffle(out)
    return out
