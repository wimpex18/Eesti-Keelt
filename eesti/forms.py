"""Two A1 topics that were in the syllabus and opened nothing.

`pohivormid` and `eitus` sat in the path with `generator=None`, so a learner who
reached them got a message saying nothing would happen. Both are A1, both are
prerequisites for topics that *are* drilled, and both are generable offline from
data the app already has -- which matters, because a generator that needs the
harvested corpus produces nothing on a fresh deployment, and these are the first
topics a beginner meets.

**Principal forms** (`nimetav, omastav, osastav` -- raamat, raamatu, raamatut)
are the three forms an Estonian dictionary lists, and every case in the language
is built on one of them. They come straight from `object_cases`, which already
holds a genitive and a partitive for 1 671 nouns whose forms differ, indexed by
Vabamorf and guarded by `test_export_quality`.

**Negation** is the other half of the object-case rule this whole app points at:
a negated verb takes the **partitive**, always, whatever the affirmative took.
`Ma ostsin raamatu` (genitive, completed) becomes `Ma ei ostnud raamatut`. So
this topic is not a detour from `obj-case` -- it is the case where the rule has
no exceptions, which makes it the easier half to learn first.

The connegative form was **measured, not assumed**. It is not the da-infinitive:
`minema` gives *minna* but negates as *ei lähe*. It is not the imperative
either, which gives *mine*. It is the present stem, and dropping the final `-n`
from the 1sg produces it for **611 of the 612** A1-B1 verbs in the wordlist --
the single divergence being `minema`, where this derivation is the correct one
and the imperative is not.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from .item import BLANK, GradedItem

LEVELS = ("A1", "A2", "B1")

#: Present-tense frames for negation. The subject is fixed at `ma` so the
#: exercise is about the verb rather than about agreement -- and Estonian
#: negation does not inflect for person, which is itself the point being
#: taught: `ei` is the same for everyone.
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

    Only nouns whose genitive and partitive actually differ: `maja, maja, maja`
    asks the learner to type the word back at itself, which teaches nothing and
    reads as a bug. `object_cases.distinct_` already carries exactly that
    distinction, and the ambiguous words -- `kool`, `reis`, `kook`, where two
    different nouns share a spelling -- are absent from that table by design,
    so they cannot be drilled here either.
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
        # Which of the three to ask for. The nominative is included because
        # recognising the citation form from two inflected ones is the skill a
        # dictionary actually demands.
        # The answer must not already be on screen. `distinct_` guarantees the
        # genitive and partitive differ, and says nothing about the nominative,
        # which frequently equals one of them: `matemaatika, matemaatika,
        # matemaatikat`, `linnapea, linnapea, linnapead`, `tigu, teo, tigu`.
        # Asking for a form that is printed beside the blank has the learner
        # copy it across and record a correct answer for a question they were
        # shown. Keep only the forms this word actually hides.
        #
        # Checked over 480 generated items: filtering on the nominative alone
        # left 41 of them still showing their own answer.
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
    """The form that follows `ei` in the present: `ostan` -> `osta`.

    Derived from the 1sg by dropping its `-n`, which is the present stem. The
    two obvious alternatives are both wrong somewhere: the da-infinitive gives
    `ei minna` and the imperative gives `ei mine`, where Estonian says
    `ei lähe`. Measured across the 612 A1-B1 verbs in the wordlist, this rule
    and the imperative agree on 611 and disagree only on `minema` -- the one
    case where the imperative is the wrong answer.
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
    """Turn an affirmative sentence negative.

    The distractor is the affirmative form the learner started from, because
    the mistake this drills against is carrying the inflected verb across the
    negation -- *ei ostan*, which is the error a Russian speaker makes, since
    Russian negates with `не` and leaves the verb agreeing.
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

#: Cases in which an Estonian adjective genuinely agrees with its noun.
#:
#: **Deliberately not all of them.** In the terminative, essive, abessive and
#: comitative the attribute stays in the *genitive* -- `suure majani`, not
#: `suureni majani` -- and Vabamorf will cheerfully synthesise the agreeing
#: form anyway, because that form exists as a word. Generating those four would
#: produce fluent, confident, wrong Estonian, which is worse than not drilling
#: them at all.
#:
#: The handbook's own example is `selle halli kivini` (terminative, attribute
#: in the genitive). This list is the conservative half: excluded cases are
#: never generated, so an error in the exception list cannot reach a learner.
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

    The error this drills is specific to a Russian speaker. Russian adjectives
    agree too, so the *concept* transfers and the learner is not warned by it
    feeling strange -- what does not transfer is that Estonian marks the
    adjective with the same case ending as the noun, across fourteen cases.
    The usual mistake is to leave the adjective in the nominative, which is why
    that is the distractor.

    The noun is shown already inflected, so the question is agreement and not
    whether the learner can decline the noun -- that is `pohivormid` and
    `kohakaanded`, and asking two things at once makes a wrong answer
    uninformative.
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
            # Nouns only, never a word that is also an adjective. `hea` is
            # tagged `adj,s`, and pairing it as the noun produced
            # `kohutavaks heaks` -- an adjective modifying an adjective, which
            # is not the construction being taught.
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
    # Sampled rather than zipped. `zip` gave exactly one attempt per adjective,
    # so a short word list -- or a run where the agreeing form happens to equal
    # the citation form -- returned far fewer items than were asked for, and
    # the caller has no way to tell "nothing to generate" from "gave up early".
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
