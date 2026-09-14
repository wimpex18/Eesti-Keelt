"""Principal forms (`pohivormid`) and negation (`eitus`): two A1 topics generated
offline, with no corpus needed.

**Principal forms** — `nimetav, omastav, osastav` (raamat, raamatu, raamatut),
the three forms every case is built on — come from `object_cases`.

**Negation** takes the partitive, always: `Ma ostsin raamatu` → `Ma ei ostnud
raamatut`. The connegative is the present stem: the 1sg minus `-n` (not the
da-infinitive `minna` or the imperative `mine`; `minema` → `ei lähe`).
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from .item import BLANK, GradedItem

LEVELS = ("A1", "A2", "B1")

#: Present-tense negation frames with the subject fixed at `ma`: `ei` does not
#: inflect for person.
PRESENT_FRAME = "Ma {} praegu."
PAST_FRAME = "Ma {} eile."


@dataclass(frozen=True)
class FormDrill(GradedItem):
    prompt: str
    answer: str
    distractor: str
    lemma: str
    label_et: str
    why_ru: str
    topic: str
    level: str | None = None

    @property
    def label(self) -> str:
        return self.label_et


# ---------------------------------------------------------------------------
# Principal forms
# ---------------------------------------------------------------------------

def principal_forms(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    only: frozenset[str] | None = None,
) -> list[FormDrill]:
    """Ask for one of the three principal forms, given the other two.

    Only nouns whose genitive and partitive differ (`object_cases.distinct_`);
    homographs such as `kool` and `reis` are absent from that table by design.
    """
    marks = ",".join("?" * len(levels))
    rows = conn.execute(
        "SELECT c.word, c.genitive, c.partitive, w.proficiency"
        "  FROM object_cases c JOIN words w ON w.word = c.word"
        f" WHERE c.distinct_ = 1 AND w.proficiency IN ({marks})"
        "   AND (',' || REPLACE(w.pos, ' ', '') || ',') LIKE '%,s,%'",
        levels,
    ).fetchall()
    if only is not None:
        rows = [r for r in rows if r[0] in only]
    if not rows:
        return []

    rnd = random.Random(seed)
    rnd.shuffle(rows)
    out: list[FormDrill] = []
    for word, gen, par, level in rows[:count]:
        # Which form to ask for: never one already shown, since the nominative often
        # equals the genitive or partitive (`linnapea, linnapea, linnapead`).
        forms = {"nimetav": word, "omastav": gen, "osastav": par}
        choices = [
            which for which, hidden in forms.items()
            if all(hidden != other for name, other in forms.items()
                   if name != which)
        ]
        if not choices:
            continue
        which = rnd.choice(choices)
        if which == "omastav":
            prompt, answer, distractor = f"{word}, {BLANK}, {par}", gen, par
            why = ("Родительный падеж (omastav) — вторая основная форма, "
                   "на ней строится большинство падежей.")
        elif which == "osastav":
            prompt, answer, distractor = f"{word}, {gen}, {BLANK}", par, gen
            why = ("Частичный падеж (osastav) — третья основная форма; "
                   "именно она нужна после отрицания и при незавершённом "
                   "действии.")
        else:
            prompt, answer, distractor = f"{BLANK}, {gen}, {par}", word, gen
            why = ("Именительный падеж (nimetav) — словарная форма, "
                   "с которой слово ищут в словаре.")
        out.append(FormDrill(
            prompt=prompt, answer=answer, distractor=distractor, lemma=word,
            label_et=which, why_ru=why, topic="pohivormid", level=level))
    return out


# ---------------------------------------------------------------------------
# Negation
# ---------------------------------------------------------------------------

def connegative(verb: str) -> str | None:
    """The form that follows `ei` in the present: `ostan` -> `osta` (the 1sg minus
    `-n`).
    """
    from .morph import synthesize

    try:
        forms = list(synthesize(verb, "n"))
    except Exception:  # noqa: BLE001 - an unanalysable verb is simply skipped
        return None
    if not forms or not forms[0].endswith("n") or len(forms[0]) < 3:
        return None
    return forms[0][:-1]


def past_participle(verb: str) -> str | None:
    """The `-nud` form, which is what `ei` takes in the past: `ei ostnud`."""
    from .morph import synthesize

    try:
        forms = list(synthesize(verb, "nud"))
    except Exception:  # noqa: BLE001
        return None
    return forms[0] if forms else None


def negation_drills(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    only: frozenset[str] | None = None,
) -> list[FormDrill]:
    """Turn an affirmative sentence negative. The distractor keeps the affirmative
    verb (*ei ostan*), the Russian-speaker's error.
    """
    marks = ",".join("?" * len(levels))
    verbs = [
        r[0] for r in conn.execute(
            "SELECT word FROM words"
            f" WHERE proficiency IN ({marks})"
            "   AND (',' || REPLACE(pos, ' ', '') || ',') LIKE '%,v,%'"
            " ORDER BY (freq_rank IS NULL OR freq_rank = 0), freq_rank",
            levels,
        )
    ]
    if only is not None:
        verbs = [v for v in verbs if v in only]
    if not verbs:
        return []

    rnd = random.Random(seed)
    # Commonest first, then shuffled within the head of the list: a beginner
    # topic should not open on the 600th most useful verb.
    pool = verbs[:max(count * 6, 60)]
    rnd.shuffle(pool)

    out: list[FormDrill] = []
    for verb in pool:
        if len(out) >= count:
            break
        from .morph import synthesize

        tense = rnd.choice(("olevik", "minevik"))
        if tense == "olevik":
            neg = connegative(verb)
            try:
                affirmative = list(synthesize(verb, "n"))
            except Exception:  # noqa: BLE001
                continue
            if not neg or not affirmative:
                continue
            prompt = PRESENT_FRAME.format(f"ei {BLANK}")
            answer, distractor = neg, affirmative[0]
            why = ("После «ei» глагол теряет личное окончание: "
                   f"«{affirmative[0]}» → «ei {neg}». "
                   "В русском отрицание не меняет форму глагола — в эстонском "
                   "меняет.")
        else:
            neg = past_participle(verb)
            try:
                affirmative = list(synthesize(verb, "sin"))
            except Exception:  # noqa: BLE001
                affirmative = []
            if not neg:
                continue
            prompt = PAST_FRAME.format(f"ei {BLANK}")
            answer = neg
            distractor = affirmative[0] if affirmative else neg
            why = ("В прошедшем времени после «ei» стоит форма на -nud, "
                   "одна для всех лиц: «ei " + neg + "».")
        out.append(FormDrill(
            prompt=prompt, answer=answer, distractor=distractor, lemma=verb,
            label_et="eitus " + tense, why_ru=why, topic="eitus", level=None))
    return out

# ---------------------------------------------------------------------------
# Agreement (ühildumine)
# ---------------------------------------------------------------------------

#: Cases in which an Estonian adjective agrees with its noun. The terminative,
#: essive, abessive and comitative are excluded: there the attribute stays in the
#: genitive (`selle halli kivini`), though Vabamorf would synthesise an agreeing
#: form.
AGREEING_CASES = (
    ("sg n", "ainsuse nimetav"), ("sg g", "ainsuse omastav"),
    ("sg p", "ainsuse osastav"), ("sg in", "sisseütlev"),
    ("sg ill", "sisseütlev"), ("sg el", "seestütlev"),
    ("sg all", "alaleütlev"), ("sg ad", "alalütlev"),
    ("sg abl", "alaltütlev"), ("sg tr", "saav"),
    ("pl n", "mitmuse nimetav"), ("pl p", "mitmuse osastav"),
)


def agreement_drills(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    only: frozenset[str] | None = None,
) -> list[FormDrill]:
    """Put the adjective into the case its noun is already in.

    The distractor is the nominative adjective. The noun is shown already inflected,
    so only agreement is tested.
    """
    marks = ",".join("?" * len(levels))
    adjectives = [
        r[0] for r in conn.execute(
            "SELECT word FROM words"
            f" WHERE proficiency IN ({marks})"
            "   AND (',' || REPLACE(pos, ' ', '') || ',') LIKE '%,adj,%'"
            " ORDER BY (freq_rank IS NULL OR freq_rank = 0), freq_rank", levels)
    ]
    nouns = [
        r[0] for r in conn.execute(
            "SELECT c.word FROM object_cases c JOIN words w ON w.word = c.word"
            f" WHERE w.proficiency IN ({marks})"
            "   AND (',' || REPLACE(w.pos, ' ', '') || ',') LIKE '%,s,%'"
            # Nouns only, never a word also tagged adjective (`hea` is `adj,s`).
            "   AND (',' || REPLACE(w.pos, ' ', '') || ',') NOT LIKE '%,adj,%'"
            " ORDER BY (w.freq_rank IS NULL OR w.freq_rank = 0), w.freq_rank",
            levels)
    ]
    if only is not None:
        nouns = [n for n in nouns if n in only]
    if not adjectives or not nouns:
        return []

    rnd = random.Random(seed)
    adj_pool = adjectives[:max(count * 8, 80)]
    noun_pool = nouns[:max(count * 8, 80)]
    rnd.shuffle(adj_pool)
    rnd.shuffle(noun_pool)

    from .morph import synthesize

    out: list[FormDrill] = []
    seen: set[tuple[str, str, str]] = set()
    # Sample pairs rather than zip, so a short list still yields the requested count.
    for _ in range(count * 40):
        if len(out) >= count:
            break
        adjective = rnd.choice(adj_pool)
        noun = rnd.choice(noun_pool)
        spec, case_et = rnd.choice(AGREEING_CASES)
        if (adjective, noun, spec) in seen:
            continue
        seen.add((adjective, noun, spec))
        try:
            adj_form = list(synthesize(adjective, spec))
            noun_form = list(synthesize(noun, spec))
            base = list(synthesize(adjective, "sg n"))
        except Exception:  # noqa: BLE001 - an unanalysable word is skipped
            continue
        if not adj_form or not noun_form or not base:
            continue
        # Nothing is being asked if the agreeing form is the citation form.
        if adj_form[0] == base[0]:
            continue
        out.append(FormDrill(
            prompt=f"{BLANK} {noun_form[0]}",
            answer=adj_form[0],
            distractor=base[0],
            lemma=adjective,
            label_et=f"ühildumine: {case_et}",
            why_ru=(
                f"Прилагательное принимает тот же падеж, что и существительное: "
                f"«{noun_form[0]}» стоит в форме «{case_et}», значит и "
                f"«{base[0]}» становится «{adj_form[0]}». В русском согласование "
                f"тоже есть, но окончания другие — и именно поэтому его легко "
                f"забыть."
            ),
            topic="uhildumine", level=None))
    return out
