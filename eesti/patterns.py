"""Comparison, numerals and question words — the closed classes.

The last three topics named in step 2 of the curriculum plan, and they need a
different treatment from the rest, because what they test is not a paradigm.

**Comparison** is a paradigm, but not one Vabamorf will synthesise: ask it for
the comparative of `suur` and it returns nothing, because Estonian comparatives
are separate lemmas in its lexicon. The rule — genitive stem plus `-m` — is easy
to write and dangerous to trust: it yields `suurem` and `väiksem` correctly, and
also `vanam` for `vanem`, `pikam` for `pikem`, and `omam` for a word that has no
comparative at all.

So the generated form is **checked against the 160 316-lemma Ekilex list, and
required to have been observed in a real corpus** (`freq_rank > 0`). That second
condition is what removes `hullum`, `täiem` and `ainsam` — all of which the
lexicon accepts as productively formed and no one says. 96 comparatives survive
at A1–B1, and the rule's failures are dropped rather than taught.

**Numerals** are not about forms at all, they are about **government**: after a
cardinal above one, the noun goes into the partitive singular — *kaks raamatut*,
not *kaks raamatud*. That is an A1 rule with an A1 error, and both forms come
straight from Vabamorf.

**Question words** are a genuinely closed class, so a table is the right
representation rather than a tax. There are about a dozen, the confusions between
them are specific and well known (`kus`/`kuhu`, `kes`/`mis`, `kellele`/`kellelt`),
and no amount of generation would improve on naming them.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from estnltk.vabamorf.morf import synthesize

from .config import LEVELS
from .item import BLANK, GradedItem
from .morph import case_forms


@dataclass(frozen=True)
class PatternDrill(GradedItem):
    prompt: str
    answer: str
    distractor: str
    lemma: str
    label_et: str
    rule: str
    why_ru: str
    topic: str
    level: str | None = None

    @property
    def label(self) -> str:
        return self.label_et


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

COMPARATIVE_FRAME = "See maja on {} kui teine."
SUPERLATIVE_FRAME = "See on {} maja meie linnas."


def comparatives(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    limit: int = 300,
) -> list[tuple[str, str, str | None]]:
    """(positive, comparative, level) for adjectives whose comparative is attested.

    Two gates, and the second is the one that matters: the candidate must be a
    lemma Ekilex knows **and** carry a non-zero frequency rank, i.e. someone has
    actually written it. Productive morphology alone accepts far too much.
    """
    marks = ",".join("?" * len(levels))
    rows = conn.execute(
        f"""SELECT word, proficiency FROM words
            WHERE proficiency IN ({marks})
              AND (','||COALESCE(pos,'')||',') LIKE '%,adj,%'
            ORDER BY (freq_rank IS NULL OR freq_rank = 0), freq_rank
            LIMIT ?""",
        (*levels, limit),
    ).fetchall()
    attested = {r[0] for r in conn.execute("SELECT word FROM words WHERE freq_rank > 0")}

    out: list[tuple[str, str, str | None]] = []
    for word, level in rows:
        forms = case_forms(word)
        if not forms:
            continue
        candidate = forms["genitive"] + "m"
        if candidate in attested and candidate != word:
            out.append((word, candidate, level))
    return out


def comparison_drills(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
) -> list[PatternDrill]:
    rng = random.Random(seed)
    pool = comparatives(conn, levels)
    if not pool:
        raise RuntimeError("no adjectives indexed — run `cli build` first")

    candidates = [(p, c, lv, kind) for p, c, lv in pool for kind in ("komp", "sup")]
    rng.shuffle(candidates)

    out: list[PatternDrill] = []
    for positive, comparative, level, kind in candidates:
        if len(out) >= count:
            break
        if kind == "komp":
            prompt = COMPARATIVE_FRAME.format(BLANK)
            answer, wrong = comparative, positive
            label, why = (
                "keskvõrre",
                f"**Keskvõrre** строится от основы генитива (omastav) + **-m**: "
                f"*{positive}* → **{comparative}**. Сравнение вводится через *kui*.",
            )
        else:
            prompt = SUPERLATIVE_FRAME.format(BLANK)
            # The superlative is analytic, and the whole lesson is that `kõige`
            # governs the *comparative*, not the positive.
            answer, wrong = f"kõige {comparative}", f"kõige {positive}"
            label, why = (
                "ülivõrre",
                f"**Ülivõrre** — это *kõige* + **keskvõrre**, а не *kõige* + "
                f"обычная форма: **kõige {comparative}**, не *kõige {positive}*.",
            )
        out.append(
            PatternDrill(prompt, answer, wrong, positive, label,
                         "comparison", why, "vordlusastmed", level)
        )
    return out


# ---------------------------------------------------------------------------
# Numerals
# ---------------------------------------------------------------------------

# Every cardinal above one governs the partitive singular, so the drill does not
# depend on which numeral is chosen — only on there being more than one.
CARDINALS = ("kaks", "kolm", "neli", "viis", "kuus", "seitse", "kaheksa", "üheksa", "kümme")

# Cardinal and its ordinal. A closed list of ten, and the irregular stems
# (kolm -> kolmanda, seitse -> seitsmenda) are where the errors live.
ORDINALS: tuple[tuple[str, str], ...] = (
    ("üks", "esimene"), ("kaks", "teine"), ("kolm", "kolmas"), ("neli", "neljas"),
    ("viis", "viies"), ("kuus", "kuues"), ("seitse", "seitsmes"),
    ("kaheksa", "kaheksas"), ("üheksa", "üheksas"), ("kümme", "kümnes"),
)

COUNT_FRAME = "Mul on {} {}."
DATE_FRAME = "Kohtume {} mail."


def _synth(lemma: str, tag: str) -> str | None:
    produced = synthesize(lemma, tag) or []
    return produced[0] if produced else None


def numeral_drills(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    topics: tuple[str, ...] = ("arvsonad", "jargarvud"),
    only: frozenset[str] | None = None,
) -> list[PatternDrill]:
    """Two rules: what a cardinal does to its noun, and how ordinals decline."""
    rng = random.Random(seed)
    out: list[PatternDrill] = []

    if "arvsonad" in topics:
        # Countable nouns only. Frequency order alone produced *"Mul on kaks
        # tähelepanu"* — two attentions — because nothing in the word list marks
        # countability. The object-case pools already enumerate concrete
        # everyday things, which is exactly the property needed, so they are
        # reused rather than a new list invented.
        from .drills import POOLS

        countable = sorted({w for pool_ in ("buyable", "edible", "readable",
                                            "findable", "watchable") for w in POOLS[pool_]})
        if only is not None:
            # A theme's own nouns are countable enough — they are concrete
            # everyday words by construction — so the theme replaces the pool
            # rather than intersecting with it, which would usually be empty.
            countable = sorted(only)
        if not countable:
            return out
        marks = ",".join("?" * len(levels))
        nouns = conn.execute(
            f"""SELECT word, proficiency FROM words
                WHERE proficiency IN ({marks})
                  AND word IN ({",".join("?" * len(countable))})""",
            (*levels, *countable),
        ).fetchall()
        pool = list(nouns)
        rng.shuffle(pool)
        for word, level in pool:
            if len(out) >= count and "jargarvud" not in topics:
                break
            partitive = _synth(word, "sg p")
            plural = _synth(word, "pl n")
            if not partitive or not plural or partitive == plural:
                continue
            numeral = rng.choice(CARDINALS)
            out.append(
                PatternDrill(
                    COUNT_FRAME.format(numeral, BLANK), partitive, plural, word,
                    "osastav pärast arvsõna", "numeral",
                    f"После количественного числительного (кроме *üks*) "
                    f"существительное стоит в **osastav ainsuses**: "
                    f"*{numeral} {partitive}*, не *{numeral} {plural}*.",
                    "arvsonad", level,
                )
            )
            if len(out) >= count:
                break

    if "jargarvud" in topics:
        pairs = list(ORDINALS)
        rng.shuffle(pairs)
        for cardinal, ordinal in pairs:
            if len(out) >= count:
                break
            answer = _synth(ordinal, "sg ad")
            wrong = _synth(cardinal, "sg ad")
            if not answer or not wrong or answer == wrong:
                continue
            out.append(
                PatternDrill(
                    DATE_FRAME.format(BLANK), answer, wrong, ordinal,
                    "järgarv, alalütlev", "numeral",
                    f"Дата требует **порядкового** числительного в alalütlev: "
                    f"*{answer}*, не количественного *{wrong}*. "
                    f"Основа меняется: *{ordinal}* → *{answer}*.",
                    "jargarvud", "A1",
                )
            )
    return out


# ---------------------------------------------------------------------------
# Question words
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Question:
    word: str
    confused_with: str
    answer_sentence: str
    frame: str
    why_ru: str


# A closed class, so this is a list rather than a generator. Each pair is a
# confusion that actually happens: the Estonian place cases split where Russian
# uses one preposition, and `kes`/`mis` splits on animacy where Russian agrees.
QUESTIONS: tuple[Question, ...] = (
    Question("Kus", "Kuhu", "Ma elan Tallinnas.", "{} sa elad?",
             "**Kus** — где (seesütlev/alalütlev). **Kuhu** — куда."),
    Question("Kuhu", "Kus", "Ma lähen Tallinna.", "{} sa lähed?",
             "**Kuhu** — куда (sisseütlev). **Kus** — где."),
    Question("Kust", "Kuhu", "Ma tulen Tallinnast.", "{} sa tuled?",
             "**Kust** — откуда (seestütlev)."),
    Question("Millal", "Kus", "Ma tulen homme.", "{} sa tuled?",
             "**Millal** — когда."),
    Question("Kes", "Mis", "See on minu vend.", "{} see on?",
             "**Kes** — о людях. **Mis** — о предметах. Эстонский различает "
             "одушевлённость там, где русский нет."),
    Question("Mis", "Kes", "See on raamat.", "{} see on?",
             "**Mis** — о предметах. **Kes** — о людях."),
    Question("Kui palju", "Millal", "See maksab viis eurot.", "{} see maksab?",
             "**Kui palju** — сколько."),
    Question("Miks", "Kuidas", "Sest ma olen väsinud.", "{} sa ei tule?",
             "**Miks** — почему. Ответ вводится через *sest*."),
    Question("Kuidas", "Miks", "Ma tulen bussiga.", "{} sa tuled?",
             "**Kuidas** — как."),
    Question("Kelle", "Kellele", "See on minu venna auto.", "{} auto see on?",
             "**Kelle** — чей (omastav). **Kellele** — кому (alaleütlev)."),
    Question("Kellele", "Kellelt", "Ma andsin raamatu vennale.", "{} sa raamatu andsid?",
             "**Kellele** — кому. **Kellelt** — от кого."),
    Question("Kellega", "Kellele", "Ma käisin kinos vennaga.", "{} sa kinos käisid?",
             "**Kellega** — с кем (kaasaütlev)."),
)


def question_drills(count: int = 10, seed: int | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    pool = list(QUESTIONS)
    rng.shuffle(pool)
    # `lemma` is deliberately empty: for every other generator the lemma is the
    # given and the form is the question, but here the word *is* the answer, so
    # putting it in the hint would print the solution above the prompt.
    return [
        PatternDrill(
            f"{q.frame.format(BLANK)} — {q.answer_sentence}",
            q.word, q.confused_with, "", "küsisõna",
            "question", q.why_ru, "kusisonad", "A1",
        )
        for q in pool[:count]
    ]
