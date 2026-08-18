"""Offline generator for object-case (obj-case) drills.

This targets the #1 documented gap in the Notion error log: choosing partitive
where a completed, whole object requires genitive. Everything here runs without
a network — templates supply the aspect context, Vabamorf supplies the real
inflected forms, so every answer is deterministic and nothing can go down.

The three rules drilled, in the order they actually bite a learner:

  1. Completed action + whole object -> GENITIVE  ("Ma lugesin raamatu labi")
  2. Ongoing / repeated / partial    -> PARTITIVE ("Ma lugesin raamatut terve ohtu")
  3. Negation                        -> ALWAYS PARTITIVE (no exceptions)

Rule 3 is exception-free, so it gives quick wins and a foothold before the
harder aspect judgement in rules 1-2.

Design note — why templates carry their own object pool. Pairing every template
with every level-appropriate noun generates grammatically valid nonsense
("Ma ostsin haigla ara" — I bought the hospital). The case rule is what is being
taught, but implausible sentences are demotivating and teach bad collocations, so
each frame declares the semantic class of object it accepts. Vocabulary breadth
is the vocab drill's job, not this one's.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import asdict, dataclass
from typing import Literal

from .config import LEVELS
from .wordlist import object_case_rows

Case = Literal["genitive", "partitive"]

# Semantic object classes. Lemmas are everyday A1-B1 vocabulary; any whose
# genitive and partitive coincide are dropped automatically at generation time,
# since the learner could not get those wrong.
POOLS: dict[str, tuple[str, ...]] = {
    "readable": ("raamat", "ajaleht", "artikkel", "kiri", "luuletus", "leping", "aruanne"),
    "buyable": (
        "pilet", "auto", "leib", "sai", "kohv", "arvuti", "telefon", "kingitus",
        "lill", "jäätis", "kook", "kleit", "särk", "jalgratas", "laud", "tool",
    ),
    "watchable": ("film", "saade", "mäng", "etendus", "seriaal", "video"),
    "findable": ("võti", "rahakott", "telefon", "dokument", "pilet", "aadress"),
    "edible": ("leib", "sai", "kook", "supp", "õun", "jäätis", "kala", "liha"),
    "doable": ("töö", "ülesanne", "kodutöö", "harjutus", "projekt", "plaan"),
}


@dataclass(frozen=True)
class Template:
    """A sentence frame whose aspect context forces exactly one case."""

    frame: str      # contains {obj}
    case: Case      # the case the frame requires
    rule: str       # rule id, used for grouping progress stats
    pool: str       # key into POOLS — which objects make sense here
    why_ru: str     # explanation in Russian, keeping the Estonian grammar terms


TEMPLATES: tuple[Template, ...] = (
    # --- Rule 1: completed action, whole object -> genitive -------------------
    Template(
        "Ma ostsin {obj} ära.", "genitive", "completed", "buyable",
        "Действие завершено, объект взят целиком → **omastav (genitiiv)**. "
        "Маркер завершённости «ära» требует полного объекта.",
    ),
    Template(
        "Ta luges {obj} läbi.", "genitive", "completed", "readable",
        "«läbi» показывает, что действие доведено до конца → **omastav (genitiiv)**.",
    ),
    Template(
        "Ma leidsin {obj} üles.", "genitive", "completed", "findable",
        "Результат достигнут, объект найден целиком → **omastav (genitiiv)**.",
    ),
    Template(
        "Homme ma teen {obj} valmis.", "genitive", "completed", "doable",
        "Будущее с результатом («valmis») → **omastav (genitiiv)**, "
        "хотя глагол стоит в форме настоящего времени.",
    ),
    Template(
        "Ma sõin {obj} ära.", "genitive", "completed", "edible",
        "Съедено целиком («ära») → **omastav (genitiiv)**. "
        "Сравни: «sõin leiba» — ел хлеб (часть, процесс).",
    ),

    # --- Rule 2: ongoing / repeated / partial -> partitive --------------------
    Template(
        "Ma ostsin {obj} iga nädal.", "partitive", "ongoing", "buyable",
        "Повторяющееся действие («iga nädal») → **osastav (partitiiv)**: "
        "регулярность исключает завершённость.",
    ),
    Template(
        "Ta vaatas {obj} terve õhtu.", "partitive", "ongoing", "watchable",
        "Длительность («terve õhtu») → **osastav (partitiiv)**: "
        "важен процесс, а не результат.",
    ),
    Template(
        "Ma otsin {obj} juba kaua.", "partitive", "ongoing", "findable",
        "Действие ещё продолжается («juba kaua») → **osastav (partitiiv)**.",
    ),
    Template(
        "Ta luges {obj} tund aega.", "partitive", "ongoing", "readable",
        "Указана длительность («tund aega»), результат не достигнут "
        "→ **osastav (partitiiv)**.",
    ),

    # --- Rule 3: negation -> always partitive ---------------------------------
    Template(
        "Ma ei ostnud {obj}.", "partitive", "negation", "buyable",
        "**Отрицание всегда требует osastav (partitiiv)** — без исключений. "
        "Самое надёжное правило: есть «ei» → партитив.",
    ),
    Template(
        "Ta ei leidnud {obj}.", "partitive", "negation", "findable",
        "После «ei» объект всегда в **osastav (partitiiv)**, "
        "независимо от завершённости действия.",
    ),
    Template(
        "Ma ei söönud {obj}.", "partitive", "negation", "edible",
        "Отрицание → **osastav (partitiiv)**, даже если по смыслу "
        "речь о целом объекте.",
    ),
)


@dataclass(frozen=True)
class Drill:
    prompt: str        # sentence with the object blanked out
    answer: str        # the correct inflected form
    distractor: str    # the other case — the mistake being trained against
    lemma: str
    case: Case
    rule: str
    why_ru: str
    level: str | None

    def to_dict(self) -> dict:
        return asdict(self)

    def check(self, given: str) -> bool:
        """Grade an answer. Deterministic — no model, no network."""
        return given.strip().lower() == self.answer.lower()

    @property
    def solution(self) -> str:
        return self.prompt.replace("____", self.answer)


def generate(
    conn: sqlite3.Connection,
    count: int = 10,
    levels: tuple[str, ...] = LEVELS,
    rules: tuple[str, ...] | None = None,
    seed: int | None = None,
) -> list[Drill]:
    """Build `count` drills, each pairing a frame with a semantically fitting noun.

    Nouns whose genitive and partitive are identical are excluded: for "maja"/
    "maja" there is no wrong answer, so such an item would measure nothing.
    """
    rng = random.Random(seed)
    templates = [t for t in TEMPLATES if not rules or t.rule in rules]
    if not templates:
        raise ValueError(f"no templates match rules={rules!r}")

    wanted = {w for t in templates for w in POOLS[t.pool]}
    forms = {
        r["word"]: r for r in object_case_rows(conn, sorted(wanted)) if r["distinct_"]
    }

    usable = [t for t in templates if any(w in forms for w in POOLS[t.pool])]
    if not usable:
        raise RuntimeError(
            "no usable templates — run `python -m eesti.cli build` to index forms."
        )

    # Enumerate every valid (frame, noun) pairing and sample without replacement,
    # so a ten-item set does not repeat the same sentence twice.
    pairings = [
        (tpl, word)
        for tpl in usable
        for word in POOLS[tpl.pool]
        if word in forms
    ]
    rng.shuffle(pairings)
    if count > len(pairings):  # small pools: allow reuse rather than short-changing
        pairings *= (count // len(pairings)) + 1

    drills: list[Drill] = []
    for tpl, word in pairings[:count]:
        row = forms[word]
        other: Case = "partitive" if tpl.case == "genitive" else "genitive"
        drills.append(
            Drill(
                prompt=tpl.frame.format(obj="____"),
                answer=row[tpl.case],
                distractor=row[other],
                lemma=row["word"],
                case=tpl.case,
                rule=tpl.rule,
                why_ru=tpl.why_ru,
                level=row["proficiency"],
            )
        )
    return drills


# --- verb-form drills (the secondary documented gap) -------------------------

VERB_FRAMES: dict[str, str] = {
    "n": "Ma ____ homme kooli.",
    "d": "Sa ____ tihti tööle.",
    "b": "Ta ____ iga päev.",
    "sin": "Eile ma ____ .",
    "s": "Eile ta ____ .",
    "nud": "Ma olen juba ____ .",
    "da": "Ma tahan ____ .",
    "ks": "Ma ____ , kui saaksin.",
}


def generate_verb_drills(
    conn: sqlite3.Connection,
    count: int = 10,
    levels: tuple[str, ...] = LEVELS,
    seed: int | None = None,
) -> list[Drill]:
    """Drills on irregular verb stems.

    The distractor is not invented: it is the form the learner would build by
    stripping `-ma` and adding the ending, which is the mistake they actually
    make (`minema` -> `minen`, where Estonian says `lähen`). Only verbs where
    that naive form is wrong are drilled.
    """
    from .verbs import irregular_verbs

    rng = random.Random(seed)
    pool = [f for f in irregular_verbs(conn, levels) if f.tag in VERB_FRAMES]
    if not pool:
        raise RuntimeError("no irregular verbs indexed — run `cli build` first")

    rng.shuffle(pool)
    if count > len(pool):
        pool *= (count // len(pool)) + 1

    return [
        Drill(
            prompt=VERB_FRAMES[form.tag].replace("____", "____"),
            answer=form.actual,
            distractor=form.naive,
            lemma=form.lemma,
            case="genitive",  # unused for verbs; kept so the shape stays uniform
            rule="verb-form",
            why_ru=(
                f"«{form.lemma}» — неправильный глагол: **{form.name}** = "
                f"*{form.actual}*, а не *{form.naive}*. "
                "Основа меняется, поэтому её нужно запомнить, "
                "а не выводить по правилу."
            ),
            level=form.level,
        )
        for form in pool[:count]
    ]
