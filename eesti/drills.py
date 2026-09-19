"""Offline generator for object-case (obj-case) drills.

Templates supply the aspect context and Vabamorf the forms, so every answer is
deterministic and offline.

  1. Completed action + whole object -> GENITIVE  ("Ma lugesin raamatu läbi")
  2. Ongoing / repeated / partial    -> PARTITIVE ("Ma lugesin raamatut terve õhtu")
  3. Negation                        -> ALWAYS PARTITIVE (no exceptions)

Each frame declares the semantic class of object it accepts, so sentences stay
plausible ("I bought the hospital" is excluded).
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from typing import Literal

from .config import LEVELS
from .item import GradedItem
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
class Drill(GradedItem):
    prompt: str        # sentence with the object blanked out
    answer: str        # the correct inflected form
    distractor: str    # the other case — the mistake being trained against
    lemma: str
    case: Case
    rule: str
    why_ru: str
    level: str | None
    # The curriculum topic these drills file under, so review handoff and the
    # progress gate treat them like any generator.
    topic: str = "obj-case"

    @property
    def label(self) -> str:
        """The form to produce, named as the exam names it (`Cloze` does the same
        through `case_et`). A review card queued before this carried the English
        name, so a later miss on the same word may add a second card for it."""
        return LABEL_ET[self.case] if self.rule != "verb-form" else "verbivorm"


#: Estonian names for the two object cases.
LABEL_ET = {"genitive": "omastav", "partitive": "osastav"}


def generate(
    conn: sqlite3.Connection,
    count: int = 10,
    levels: tuple[str, ...] = LEVELS,
    rules: tuple[str, ...] | None = None,
    seed: int | None = None,
) -> list[Drill]:
    """Build `count` drills, each pairing a frame with a semantically fitting noun;
    nouns whose genitive and partitive are identical are excluded.
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

    # Deal pairings round-robin across shuffled frames (nouns shuffled within each),
    # so a set repeats no sentence until the frames run out, then spreads repeats.
    by_frame: dict[str, list] = {}
    for tpl in usable:
        pool = [(tpl, word) for word in POOLS[tpl.pool] if word in forms]
        if pool:
            rng.shuffle(pool)
            by_frame.setdefault(tpl.frame, []).extend(pool)

    queues = list(by_frame.values())
    rng.shuffle(queues)
    pairings = []
    round_ = 0
    while len(pairings) < count:
        drawn = 0
        for q in queues:
            if round_ < len(q):
                pairings.append(q[round_])
                drawn += 1
                if len(pairings) == count:
                    break
        if drawn == 0:  # every frame exhausted: reuse rather than short-change
            round_ = 0
            if not any(queues):
                break
            continue
        round_ += 1

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
                topic="obj-case",
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
    """Drills on irregular verb stems: the distractor is the naive form (`minema` →
    `minen`, not `lähen`); only verbs where it is wrong are drilled.
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
            topic="verb-form",
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


#: Object-case sub-rules as the learner reads them (the Vaba harjutus select
#: offers the same three).
RULE_ET = {
    "negation": "eitus → osastav",
    "completed": "lõpetatud → omastav",
    "ongoing": "kestev → osastav",
    "verb-form": "verbivorm",
}
