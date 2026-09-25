"""Pronoun declension, and the `asesonad` drill.

Vabamorf declines pronouns wrongly (`mina` → genitive `mina`), so these forms
are not synthesised. They are the EKI teatmik's own tables (*Asesõnade
käänamine*, tables 1–5), with its stress and stem marks removed. Parallel forms
keep EKI's order and `~`: long first, short second. `sina` and `teie` are not
printed separately there; the teatmik groups *mina, sina* and *meie, teie* as
declining alike, so they are the `mina` table with m → s and me → te, which is
what that grouping states.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .item import BLANK, GradedItem

SOURCE = "https://teatmik.eki.ee/teatmik/asesonade-kaanamine/"

CASES = ("nimetav", "omastav", "osastav", "sisseütlev", "seesütlev", "seestütlev",
         "alaleütlev", "alalütlev", "alaltütlev", "saav", "rajav", "olev",
         "ilmaütlev", "kaasaütlev")

#: pronoun -> (singular forms, plural forms), in `CASES` order.
_MINA_SG = ("mina ~ ma", "minu ~ mu", "mind", "minusse ~ musse", "minus ~ mus",
            "minust ~ must", "minule ~ mulle", "minul ~ mul", "minult ~ mult",
            "minuks", "minuni", "minuna", "minuta", "minuga ~ muga")
_MEIE = ("meie ~ me", "meie ~ me", "meid", "meisse", "meis", "meist", "meile",
         "meil", "meilt", "meieks ~ meiks", "meieni", "meiena", "meieta", "meiega")
_TEMA_SG = ("tema ~ ta", "tema ~ ta", "teda", "temasse ~ tasse", "temas ~ tas",
            "temast ~ tast", "temale ~ talle", "temal ~ tal", "temalt ~ talt",
            "temaks", "temani", "temana", "temata", "temaga ~ taga")
_NEMAD = ("nemad ~ nad", "nende", "neid", "nendesse ~ neisse", "nendes ~ neis",
          "nendest ~ neist", "nendele ~ neile", "nendel ~ neil", "nendelt ~ neilt",
          "nendeks ~ neiks", "nendeni", "nendena", "nendeta", "nendega")
_SEE_SG = ("see", "selle", "seda", "sellesse ~ sesse", "selles ~ ses",
           "sellest ~ sest", "sellele", "sellel ~ sel", "sellelt ~ selt",
           "selleks ~ seks", "selleni", "sellena", "selleta", "sellega ~ seega")
_MIS = ("mis", "mille", "mida", "millesse", "milles", "millest", "millele",
        "millel ~ mil", "millelt ~ milt", "milleks", "milleni", "millena",
        "milleta", "millega ~ miska")


def _swap(forms: tuple[str, ...], old: str, new: str) -> tuple[str, ...]:
    return tuple(" ~ ".join(new + v[len(old):] if v.startswith(old) else v
                            for v in f.split(" ~ ")) for f in forms)


TABLES: dict[str, tuple[str, tuple[str, ...]]] = {
    "mina": ("ainsus", _MINA_SG),
    "sina": ("ainsus", _swap(_swap(_MINA_SG, "mi", "si"), "m", "s")),
    "tema": ("ainsus", _TEMA_SG),
    "meie": ("mitmus", _MEIE),
    "teie": ("mitmus", _swap(_swap(_MEIE, "mei", "tei"), "me", "te")),
    "nemad": ("mitmus", _NEMAD),
    "see": ("ainsus", _SEE_SG),
    "mis": ("ainsus", _MIS),
}


def form(pronoun: str, case: str) -> str:
    return TABLES[pronoun][1][CASES.index(case)]


def table() -> dict:
    """The personal pronouns side by side, for the Reegel page."""
    cols = ("mina", "sina", "tema", "meie", "teie", "nemad")
    return {"columns": ["", *cols],
            "rows": [[case, *(form(p, case) for p in cols)] for case in CASES]}


@dataclass(frozen=True)
class PronounDrill(GradedItem):
    prompt: str
    answer: str           # EKI's cell, parallel forms joined by " ~ "
    distractor: str
    lemma: str
    label_et: str
    rule: str
    why_ru: str
    topic: str = "asesonad"
    level: str | None = "A1"

    @property
    def label(self) -> str:
        return self.label_et


#: case, frame, pronouns that fit, and why (examples from EKK M 8, M 57, M 59).
FRAMES = (
    ("alaleütlev", "Anna see raamat {}.", ("mina", "tema", "meie", "nemad"),
     "Кому? — **alaleütlev**: *Anna see mulle (või minule)!*"),
    ("alalütlev", "{} on kaks last.", ("mina", "sina", "tema", "meie", "teie", "nemad"),
     "У кого есть — **alalütlev**: *Maril on kaks last* → *{a} on kaks last*."),
    ("osastav", "Ma ootan {}.", ("sina", "tema", "teie", "nemad"),
     "*ootama* требует **osastav**: *ootan {a}*."),
    ("seestütlev", "Me räägime {}.", ("sina", "tema", "nemad"),
     "О ком? — **seestütlev**: *räägime {a}*."),
    ("kaasaütlev", "Ma tulen {}.", ("sina", "tema", "teie", "nemad"),
     "С кем? — **kaasaütlev**: *tulen {a}*."),
    ("omastav", "See on {} auto.", ("mina", "sina", "tema", "nemad"),
     "Чей? — **omastav**: *{a} auto*."),
)


def drills(count: int = 10, seed: int | None = None) -> list[PronounDrill]:
    rng = random.Random(seed)
    out: list[PronounDrill] = []
    for i in range(count * 4):
        if len(out) >= count:
            break
        case, frame, pool, why = FRAMES[i % len(FRAMES)]
        pronoun = rng.choice(pool)
        answer = form(pronoun, case)
        first = answer.split(" ~ ")[0]
        prompt = frame.format(BLANK)
        wrong = form(pronoun, "nimetav").split(" ~ ")[0]
        item = PronounDrill(prompt, answer, wrong, pronoun, case, case,
                            why.format(a=first.capitalize() if prompt.startswith(BLANK)
                                       else first))
        if all((item.prompt, item.lemma) != (o.prompt, o.lemma) for o in out):
            out.append(item)
    rng.shuffle(out)
    return out
