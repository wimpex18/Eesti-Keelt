"""`osaalus`: the partitive subject of an existential sentence.

Two rules from EKK SÜ 35 (*Täis- ja osaalus*), each settled by the sentence alone:

- **eitus** — a negated subject is always partitive: *Laual pole raamatut*,
  *Poes ei ole leiba*. EKI's grammar profile places it at A1–A2 (913, 1336).
- **mitmus** — a partial subject does not agree with the verb, which stays in
  the third person singular: *Pargis mängib lapsi*, but *Pargis mängivad
  lapsed*. The verb's number decides. EKI's profile places varying the subject's
  case at B2 (1328), so a set asks for it only by name.

An affirmative subject of substance may be either case (*Vaadis on
bensiin/bensiini*), so no item asks for one: the rule page shows *Poes on leiba*
as an example, and nothing grades it. Forms are Vabamorf's (`morph.unique_form`).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .item import BLANK
from .morph import unique_form
from .patterns import PatternDrill

#: The rules a set draws when none is named.
BASE_RULES = ("eitus",)


@dataclass(frozen=True)
class Frame:
    text: str              # contains BLANK
    rule: str
    nouns: tuple[str, ...]
    answer: str            # the tag the frame requires
    against: str           # the tag a learner reaches for
    why_ru: str


FRAMES: tuple[Frame, ...] = (
    Frame(f"Poes ei ole {BLANK}.", "eitus",
          ("leib", "piim", "sai", "juust", "mahl"), "sg p", "sg n",
          "В отрицательном предложении о наличии подлежащее (**alus**) всегда в "
          "**osastav**: *Poes ei ole leiba*."),
    Frame(f"Külmkapis pole {BLANK}.", "eitus",
          ("piim", "juust", "või", "mahl"), "sg p", "sg n",
          "*pole* = *ei ole*: того, чего нет, — в **osastav** (частичный падеж): "
          "*Külmkapis pole piima*."),
    Frame(f"Laual ei ole {BLANK}.", "eitus",
          ("raamat", "tass", "taldrik", "ajaleht", "võti", "vihik"), "sg p", "sg n",
          "Отрицание наличия → подлежащее в **osastav**, даже если речь об "
          "одном предмете: *Laual pole raamatut*."),
    Frame(f"Klassis pole {BLANK}.", "eitus",
          ("õpetaja", "arvuti", "tool"), "sg p", "sg n",
          "Нет кого-то или чего-то → **osastav**: *Klassis pole õpetajat*."),

    Frame(f"Pargis mängib {BLANK}.", "mitmus", ("laps", "tüdruk"), "pl p", "pl n",
          "Глагол *mängib* в ед. ч., значит подлежащее частичное (**osaalus**): "
          "**mitmuse osastav** *lapsi*. С *mängivad* было бы *lapsed*."),
    Frame(f"Pargis mängivad {BLANK}.", "mitmus", ("laps", "tüdruk"), "pl n", "pl p",
          "Глагол во мн. ч. (*mängivad*) согласуется только с полным подлежащим: "
          "**mitmuse nimetav** *lapsed*. Частичное подлежащее не согласуется."),
    Frame(f"Külas elab {BLANK}.", "mitmus", ("inimene", "pere"), "pl p", "pl n",
          "*elab* — 3-е лицо ед. ч. при множестве людей: подлежащее частичное "
          "(**osaalus**), **mitmuse osastav**: *Külas elab inimesi*."),
    Frame(f"Külas elavad {BLANK}.", "mitmus", ("inimene", "pere"), "pl n", "pl p",
          "*elavad* согласуется с полным подлежащим: **mitmuse nimetav** "
          "(*Külas elavad inimesed*)."),
    Frame(f"Klassis istub {BLANK}.", "mitmus", ("õpilane", "laps"), "pl p", "pl n",
          "Частичное подлежащее (**osaalus**) не согласуется с глаголом: "
          "*istub* + **mitmuse osastav** *õpilasi*."),
    Frame(f"Klassis istuvad {BLANK}.", "mitmus", ("õpilane", "laps"), "pl n", "pl p",
          "*istuvad* — мн. ч., значит подлежащее полное: **mitmuse nimetav** "
          "*õpilased*."),
    Frame(f"Laual lebab {BLANK}.", "mitmus", ("raamat", "vihik"), "pl p", "pl n",
          "*lebab* в ед. ч. при нескольких предметах → **osaalus** в **mitmuse "
          "osastav**: *Laual lebab raamatuid*."),
)

_CASE = {"sg p": "osastav", "sg n": "nimetav",
         "pl p": "mitmuse osastav", "pl n": "mitmuse nimetav"}


def _item(frame: Frame, noun: str) -> PatternDrill | None:
    answer, wrong = unique_form(noun, frame.answer), unique_form(noun, frame.against)
    if not answer or not wrong or answer == wrong:
        return None
    # Always a choice: typed, *Pargis mängib laps* (one child) and *Poes ei ole
    # saiu* (plural) are Estonian too, and the hidden case could not say which.
    return PatternDrill(frame.text, answer, wrong, noun, _CASE[frame.answer],
                        frame.rule, frame.why_ru, "osaalus",
                        choices=tuple(sorted((answer, wrong))))


def drills(count: int = 10, seed: int | None = None,
           rules: tuple[str, ...] | None = None) -> list[PatternDrill]:
    """`count` items over the named rules, no sentence twice while others remain."""
    wanted = rules or BASE_RULES
    pool = [item for frame in FRAMES if frame.rule in wanted
            for item in (_item(frame, noun) for noun in frame.nouns) if item]
    if not pool:
        return []
    rng = random.Random(seed)
    rng.shuffle(pool)
    out: list[PatternDrill] = []
    while len(out) < count:
        out.extend(pool[:count - len(out)])
    return out
