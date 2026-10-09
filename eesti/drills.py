"""Offline generator for object-case (obj-case) drills.

Templates supply the aspect context and Vabamorf the forms, so every answer is
deterministic and offline.

  1. Completed action + whole object -> GENITIVE  ("Ma lugesin raamatu läbi")
  2. Ongoing / repeated / partial    -> PARTITIVE ("Ma lugesin raamatut terve õhtu")
  3. Negation                        -> ALWAYS PARTITIVE (no exceptions)

The total object is NOMINATIVE under any one of four conditions (EKK SÜ 40; EKI
Teatmik, *Täissihitise kääne*): a plural object, a command, the impersonal, and
an object of a *da*-infinitive that is not itself the verb's object (*Tuleb
leib ära osta*, but *Ma tahan leiva ära osta*). Those rules sit above A1 in EKI's
grammar profile, so a set asks for them only by name (`BASE_RULES`).

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

Case = Literal["genitive", "partitive", "nominative"]

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
    # Countable things, for a plural object: "kõik kohvid" is a different claim.
    "countable": (
        "pilet", "leib", "sai", "kingitus", "lill", "kook", "kleit", "särk",
        "tool", "laud", "telefon", "jalgratas",
    ),
    "countable_edible": ("leib", "sai", "kook", "õun", "jäätis"),
}


@dataclass(frozen=True)
class Template:
    """A sentence frame whose context forces exactly one case."""

    frame: str      # contains {obj}
    case: Case      # the case the frame requires
    rule: str       # rule id, used for grouping progress stats
    pool: str       # key into POOLS — which objects make sense here
    why_ru: str     # explanation in Russian, keeping the Estonian grammar terms
    # The form offered against it: the mistake being trained. Genitive and
    # partitive stand against each other; a nominative against the genitive a
    # learner reaches for after "completed → omastav".
    against: Case | None = None
    number: str = "sg"

    @property
    def other(self) -> Case:
        if self.against:
            return self.against
        return "partitive" if self.case == "genitive" else "genitive"


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

    # --- The nominative total object (EKK SÜ 40; EKI Teatmik) ------------------
    # Rule 4: a command.
    Template(
        "Osta {obj} ära!", "nominative", "imperative", "buyable",
        "Приказ (**käskiv kõneviis**): täissihitis стоит в **nimetav** "
        "(именительный падеж), не в omastav: *Osta leib ära!*",
        against="genitive",
    ),
    Template(
        "Loe {obj} läbi!", "nominative", "imperative", "readable",
        "При приказе полное дополнение — **nimetav**: *Loe raamat läbi!* "
        "Сравни: *Ma lugesin raamatu läbi* (omastav).",
        against="genitive",
    ),
    Template(
        "Leia {obj} üles!", "nominative", "imperative", "findable",
        "**Käskiv kõneviis** → täissihitis в **nimetav**: *Leia võti üles!*",
        against="genitive",
    ),
    Template(
        "Söö {obj} ära!", "nominative", "imperative", "edible",
        "Приказ → **nimetav**: *Söö kook ära!* "
        "Сравни: *Ma sõin koogi ära* (omastav).",
        against="genitive",
    ),
    Template(
        "Tee {obj} valmis!", "nominative", "imperative", "doable",
        "Приказ → täissihitis в **nimetav**: *Tee töö valmis!*",
        against="genitive",
    ),

    # Rule 5: the impersonal.
    Template(
        "Eile osteti {obj} ära.", "nominative", "impersonal", "buyable",
        "**Umbisikuline tegumood** (безличный залог, *osteti*): "
        "täissihitis стоит в **nimetav**, не в omastav.",
        against="genitive",
    ),
    Template(
        "Lõpuks leiti {obj} üles.", "nominative", "impersonal", "findable",
        "Безличная форма *leiti* → täissihitis в **nimetav**: "
        "*Võti leiti üles*.",
        against="genitive",
    ),
    Template(
        "Õhtul söödi {obj} ära.", "nominative", "impersonal", "edible",
        "**Umbisikuline tegumood** (*söödi*) → **nimetav**. "
        "Сравни: *Me sõime koogi ära* (omastav).",
        against="genitive",
    ),
    Template(
        "Homseks tehakse {obj} valmis.", "nominative", "impersonal", "doable",
        "Безличная форма *tehakse* → täissihitis в **nimetav**, "
        "даже когда результат в будущем.",
        against="genitive",
    ),

    # Rule 6: the object of a da-infinitive, unless the infinitive is itself the
    # verb's object (Teatmik: *pere otsustas kutsika võtta*).
    Template(
        "Mul on vaja {obj} ära osta.", "nominative", "infinitive", "buyable",
        "Дополнение при **da-tegevusnimi** (da-инфинитиве) после *on vaja* "
        "стоит в **nimetav**: *Mul on vaja leib ära osta*.",
        against="genitive",
    ),
    Template(
        "Sul tuleb {obj} läbi lugeda.", "nominative", "infinitive", "readable",
        "После *tuleb* + **da-tegevusnimi** täissihitis — **nimetav**: "
        "*Sul tuleb raamat läbi lugeda*.",
        against="genitive",
    ),
    Template(
        "Homme tuleb {obj} valmis teha.", "nominative", "infinitive", "doable",
        "*tuleb* + **da-tegevusnimi** → täissihitis в **nimetav**.",
        against="genitive",
    ),
    Template(
        "Ma tahan {obj} ära osta.", "genitive", "infinitive", "buyable",
        "Здесь da-инфинитив *osta* сам служит дополнением глагола *tahan*, "
        "поэтому täissihitis остаётся в **omastav**: *Ma tahan leiva ära osta*. "
        "Сравни: *Mul on vaja leib ära osta* (nimetav).",
        against="nominative",
    ),
    Template(
        "Ma otsustasin {obj} läbi lugeda.", "genitive", "infinitive", "readable",
        "*Otsustasin* + da-инфинитив: инфинитив сам — дополнение глагола, "
        "поэтому **omastav**, как в примере EKI *pere otsustas kutsika võtta*.",
        against="nominative",
    ),

    # Rule 7: a plural total object.
    Template(
        "Ma ostsin kõik {obj} ära.", "nominative", "plural", "countable",
        "**Mitmus**: полное дополнение во множественном числе стоит в "
        "**nimetav** (*leivad*), не в omastav (*leibade*).",
        against="genitive", number="pl",
    ),
    Template(
        "Ta luges kõik {obj} läbi.", "nominative", "plural", "readable",
        "Täissihitis во мн. ч. — **mitmuse nimetav**: *Ta luges kõik "
        "raamatud läbi*.",
        against="genitive", number="pl",
    ),
    Template(
        "Ma leidsin kõik {obj} üles.", "nominative", "plural", "findable",
        "Все найдены, объект во мн. ч. → **mitmuse nimetav**: "
        "*Ma leidsin kõik võtmed üles*.",
        against="genitive", number="pl",
    ),
    Template(
        "Lapsed sõid kõik {obj} ära.", "nominative", "plural", "countable_edible",
        "Съели всё, объект во мн. ч. → **mitmuse nimetav** (*koogid*), "
        "не omastav (*kookide*).",
        against="genitive", number="pl",
    ),
)

#: The rules a set draws when none is named: the A1 contrast between omastav and
#: osastav. The nominative rules are EKI's A2 and above (statements 1288, 1300,
#: 879), so they come by name, from a unit revisit or the rule picker.
BASE_RULES = ("completed", "ongoing", "negation")

#: Tags for the forms a frame can ask for.
_TAG = {("genitive", "sg"): "sg g", ("partitive", "sg"): "sg p",
        ("nominative", "sg"): "sg n", ("genitive", "pl"): "pl g",
        ("partitive", "pl"): "pl p", ("nominative", "pl"): "pl n"}


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
    number: str = "sg"
    #: Set for the nominative rules, which are always a choice: typed, *Osta
    #: leivad ära!* is Estonian too, and the hidden case could not say which.
    choices: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        """The form to produce, named as the exam names it (`Cloze` does the same
        through `case_et`). A review card queued before this carried the English
        name, so a later miss on the same word may add a second card for it."""
        if self.rule == "verb-form":
            return "verbivorm"
        name = LABEL_ET[self.case]
        return f"mitmuse {name}" if self.number == "pl" else name


#: Estonian names for the object cases.
LABEL_ET = {"genitive": "omastav", "partitive": "osastav", "nominative": "nimetav"}


def _forms(lemma: str) -> dict[tuple[str, str], str]:
    """Every form a frame may ask of `lemma`, each read back by Vabamorf."""
    from .morph import unique_form

    out = {}
    for key, tag in _TAG.items():
        form = unique_form(lemma, tag)
        if form:
            out[key] = form
    return out


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
    templates = [t for t in TEMPLATES if t.rule in (rules or BASE_RULES)]
    if not templates:
        raise ValueError(f"no templates match rules={rules!r}")

    wanted = {w for t in templates for w in POOLS[t.pool]}
    rows = {r["word"]: r for r in object_case_rows(conn, sorted(wanted))}

    def fits(tpl: Template, word: str) -> bool:
        """Both forms are known and differ: an item that cannot be got wrong
        measures nothing."""
        row = rows.get(word)
        if row is None:
            return False
        if tpl.case != "nominative" and tpl.other != "nominative" and tpl.number == "sg":
            return bool(row["distinct_"])
        forms = _forms(word)
        a, b = forms.get((tpl.case, tpl.number)), forms.get((tpl.other, tpl.number))
        return bool(a and b and a != b)

    forms = {w for w in wanted if any(fits(t, w) for t in templates if w in POOLS[t.pool])}

    usable = [t for t in templates if any(fits(t, w) for w in POOLS[t.pool])]
    if not usable:
        raise RuntimeError(
            "no usable templates — run `python -m eesti.cli build` to index forms."
        )

    # Deal pairings round-robin across shuffled frames (nouns shuffled within each),
    # so a set repeats no sentence until the frames run out, then spreads repeats.
    by_frame: dict[str, list] = {}
    for tpl in usable:
        pool = [(tpl, word) for word in POOLS[tpl.pool] if word in forms and fits(tpl, word)]
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
        row = rows[word]
        if tpl.case == "nominative" or tpl.other == "nominative" or tpl.number == "pl":
            made = _forms(word)
            answer, distractor = made[(tpl.case, tpl.number)], made[(tpl.other, tpl.number)]
        else:
            answer, distractor = row[tpl.case], row[tpl.other]
        drills.append(
            Drill(
                prompt=tpl.frame.format(obj="____"),
                answer=answer,
                distractor=distractor,
                lemma=row["word"],
                case=tpl.case,
                rule=tpl.rule,
                why_ru=tpl.why_ru,
                level=row["proficiency"],
                topic="obj-case",
                number=tpl.number,
                choices=(tuple(sorted((answer, distractor)))
                         if tpl.rule not in BASE_RULES else ()),
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
    "imperative": "käskiv → nimetav",
    "impersonal": "umbisikuline → nimetav",
    "infinitive": "da-tegevusnimi → nimetav",
    "plural": "mitmus → nimetav",
    "verb-form": "verbivorm",
}
