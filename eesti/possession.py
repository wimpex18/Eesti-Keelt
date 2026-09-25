"""*Mul on*, *mulle meeldib*, *mul on vaja* (`mul-on`): who has, who likes,
who needs.

EKK M 59 and the syntax chapter: the owner is in `alalütlev` (*Maril on kaks
last*); in a negative sentence the thing is in `osastav` (*Laual pole
raamatut*). EKI's learner dictionary (PSV): *meeldima* — *kellele?*, *mida
teha?* (*See tüdruk meeldib mulle väga*, *Talle meeldib tantsida*); *vaja* —
*mida?*, *mida teha?* (*Mul on uut rahakotti vaja*, *Meil oli vaja maale
sõita*). Nouns and verbs are synthesised by Vabamorf; pronouns come from the
EKI teatmik table (`eesti/pronouns.py`).
"""

from __future__ import annotations

import random

from .item import BLANK
from .morph import synthesize
from .patterns import PatternDrill
from .pronouns import form

NOUNS = ("auto", "aeg", "korter", "jalgratas", "arvuti", "vihmavari")
VERBS = ("tantsima", "ujuma", "lugema", "sõitma", "magama", "puhkama")


def _one(word: str, tag: str) -> str | None:
    found = synthesize(word, tag) or []
    return found[0] if len(set(found)) == 1 else None


def _no(rng) -> PatternDrill | None:
    noun = rng.choice(NOUNS)
    answer = _one(noun, "sg p")
    if not answer:
        return None
    return PatternDrill(f"Mul ei ole {BLANK}.", answer, noun, noun, "keda? mida?", "eitus",
                        f"«У меня нет» — то, чего нет, в **osastav**: *Mul ei ole {answer}* "
                        "(как *Laual pole raamatut*).", "mul-on", "A1")


def _likes(rng) -> PatternDrill | None:
    verb = rng.choice(VERBS)
    answer, wrong = _one(verb, "da"), _one(verb, "ma")
    if not answer or not wrong:
        return None
    return PatternDrill(f"Mulle meeldib {BLANK}.", answer, wrong, verb, "mida teha?", "meeldima",
                        f"*meeldima* + **da-инфинитив**: *Mulle meeldib {answer}* "
                        "(как *Talle meeldib tantsida*).", "mul-on", "A1")


def _needs(rng) -> PatternDrill | None:
    verb = rng.choice(VERBS)
    answer, wrong = _one(verb, "da"), _one(verb, "ma")
    if not answer or not wrong:
        return None
    return PatternDrill(f"Mul on vaja {BLANK}.", answer, wrong, verb, "mida teha?", "vaja",
                        f"*vaja* + **da-инфинитив**: *Mul on vaja {answer}* "
                        "(как *Meil oli vaja maale sõita*).", "mul-on", "A1")


def _who_likes(rng) -> PatternDrill | None:
    pronoun = rng.choice(("mina", "sina", "tema", "meie", "nemad"))
    answer = form(pronoun, "alaleütlev")
    first = answer.split(" ~ ")[-1]
    return PatternDrill(f"See film meeldib {BLANK}.", answer, pronoun, pronoun, "kellele?",
                        "meeldima",
                        f"Кому нравится — **alaleütlev**: *meeldib {first}* "
                        "(как *See tüdruk meeldib mulle väga*). Не *{pronoun} meeldib*.".format(
                            pronoun=pronoun), "mul-on", "A1")


def drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    makers = (_no, _likes, _needs, _who_likes)
    out: list[PatternDrill] = []
    for i in range(count * 4):
        if len(out) >= count:
            break
        item = makers[i % len(makers)](rng)
        if item and all((item.prompt, item.answer) != (o.prompt, o.answer) for o in out):
            out.append(item)
    rng.shuffle(out)
    return out
