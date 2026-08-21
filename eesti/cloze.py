"""Drills built from sentences Estonians actually wrote.

Every drill in this project so far came out of a template I wrote by hand. That
caps variety at my imagination and it has already gone wrong once: pairing every
frame with every level-appropriate noun produced *"Ma ostsin haigla ära"* — "I
bought the hospital" — until each template had to declare a semantic pool of
objects it accepts. Maintaining those pools is a permanent tax, and the ceiling
is still a few dozen frames.

There are **2 073 usable sentences** of real Estonian already on disk, harvested
from Selges keeles and lemmatised by Vabamorf. Blanking a word in one of those
gives a drill with no pool to maintain and a guarantee no template can offer:
**the answer is correct because a native speaker wrote it.** This is
Clozemaster's move, done against a corpus that is already graded for difficulty.

## The trap, and how the answer stays decidable

The obvious version of this is unsafe. Blank the object in *"Ta luges raamatut"*
and ask genitive-or-partitive, and you are asserting that the genitive would be
wrong — which depends on telicity, which is semantics, not morphology. Estonian
frequently licenses both. A drill that marks a licit answer wrong is worse than
no drill: it teaches a rule that does not exist.

So an item is generated only where the target form is **forced**, by one of two
routes:

1. **The prompt names the case.** *"Ma elan ____ (Tallinn, seesütlev)"* has
   exactly one answer, because the case is given and morphology decides the rest.
   Nothing is being claimed about which case the sentence needed — the learner is
   asked to produce a form, which is the skill the error log actually records.
2. **A trigger makes the case obligatory.** Under negation the partitive is
   exception-free — the one object-case rule that needs no aspect judgement.
   That, and only that, is generated as a genitive/partitive choice.

Anything else stays with the templates, which can supply the aspect context that
a corpus sentence leaves implicit.

## Why the wrong answer is not invented

The distractor is the same case built from the **nominative stem instead of the
genitive stem** — `sõber` + `-s` gives `sõbers` where Estonian says `sõbras`.
That is not a plausible-looking decoy; it is the error, and it is the reason
`gen-stem` sits upstream of eleven other topics in the curriculum graph. Where
the naive form happens to be right, there is no contrast and no multiple-choice
item — the same rule that drops `kino` from the object-case pool.

## Three gates before an item ships

Corpus text is not clean, and a wrong "correct answer" is the worst possible
output. So each candidate must pass:

* **unambiguous lemma** — a token that reads as two different lemmas cannot be
  pinned by naming one of them in the prompt;
* **round-trip** — Vabamorf's synthesis of `(lemma, case)` must reproduce the
  attested surface form exactly. Where the corpus and the synthesiser disagree,
  something is wrong with one of them and the item is dropped rather than
  guessed at. This is also what keeps grading deterministic;
* **a real contrast** — answer and distractor must differ.
"""

from __future__ import annotations

import random
import re
import sqlite3
from dataclasses import dataclass

from estnltk.vabamorf.morf import synthesize

from .config import LEVELS
from .item import BLANK, GradedItem
from .morph import _readings, analyze, case_forms, split_sentences

# Vabamorf case tags -> the Estonian name (what the exam uses) and a Russian
# gloss (what the learner will recognise). Nominative and the short illative are
# deliberately absent: the nominative is the prompt's own citation form, and the
# short illative is optional in a way that makes "the" answer a fiction.
CASES: dict[str, tuple[str, str]] = {
    "sg g": ("omastav", "родительный"),
    "sg p": ("osastav", "частичный"),
    "sg ill": ("sisseütlev", "иллатив (куда)"),
    "sg in": ("seesütlev", "инессив (где, внутри)"),
    "sg el": ("seestütlev", "элатив (откуда, изнутри)"),
    "sg all": ("alaleütlev", "аллатив (кому, на что)"),
    "sg ad": ("alalütlev", "адессив (у кого, на чём)"),
    "sg abl": ("alaltütlev", "аблатив (от кого, с чего)"),
    "sg tr": ("saav", "транслатив (кем/чем становится)"),
    "sg ter": ("rajav", "терминатив (до)"),
    "sg es": ("olev", "эссив (в качестве)"),
    "sg ab": ("ilmaütlev", "абессив (без)"),
    "sg kom": ("kaasaütlev", "комитатив (с кем/чем)"),
    "pl g": ("omastav mitmuses", "родительный мн."),
    "pl p": ("osastav mitmuses", "частичный мн."),
    "pl in": ("seesütlev mitmuses", "инессив мн."),
    "pl ad": ("alalütlev mitmuses", "адессив мн."),
}

# Which curriculum topic each case belongs to, so a generated item can be filed
# against the syllabus rather than floating free.
TOPIC_CASES: dict[str, tuple[str, ...]] = {
    "gen-stem": ("sg g",),
    "osastav": ("sg p",),
    "kohakaanded": ("sg ill", "sg in", "sg el", "sg all", "sg ad", "sg abl"),
    "harvad-kaanded": ("sg tr", "sg ter", "sg es", "sg ab", "sg kom"),
    "mitmus": ("pl g", "pl p", "pl in", "pl ad"),
}

# Negation words. `ära` is the imperative negator; `pole`/`polnud` are the
# contracted forms of "ei ole", which Vabamorf lemmatises as "olema".
NEGATORS = frozenset({"ei", "ega", "ära", "ärge", "ärgem", "ärme"})
_CONTRACTED = frozenset({"pole", "polnud", "poleks", "polevat"})

# Negation scopes over its own clause, not the sentence. Without this the
# generator produced *"Kui jahipidamisõigust tõendavad dokumendid ..., siis ei
# pea ..."* as a negation item: the partitive is right, but it has nothing to do
# with the `ei` in the other clause, so the explanation would have taught a
# connection that is not there. Splitting on punctuation and clause-introducing
# words is crude next to real parsing, and errs towards dropping items.
_CLAUSE_RE = re.compile(
    r"[,;:—–]|\b(?:kui|et|sest|kuid|aga|siis|mis|mida|kes|keda|kuna|ehkki|"
    r"kuigi|ning|või)\b",
    re.IGNORECASE,
)

# Re-exported, not redefined. `item.BLANK` is the one definition; a second
# literal here is the same duplication as the four private `_TAG_RE`s that
# gave one line of input three different answers.
_WORD_RE = re.compile(r"\w", re.UNICODE)


@dataclass(frozen=True)
class Cloze(GradedItem):
    """One item. Same surface as `drills.Drill`, plus where it came from.

    It said "same surface" and meant it literally: this class predated
    `item.GradedItem` and carried its own copy of `check`, `solution`,
    `reference` and `to_dict` — the five methods that mixin exists to keep
    identical across generators. Four of the five had already drifted apart in
    one way or another, and the fifth was simply missing, which is how a cloze
    item reached the page with no case in its instruction row.

    Measured over 425 real items before removing the copies: `check` graded
    the same for every answer (`lower` and `casefold` differ on no Estonian
    letter), `reference` returned the same object for all 425, and no prompt
    could open with the blank — the round-trip gate rejects a capitalised
    common noun, so the mixin's sentence-initial capitalisation is a defence
    rather than a change. `hint` is still overridden, because for rection the
    case is the question and the em dash says so.
    """

    prompt: str          # the sentence with one word replaced by ____
    answer: str          # the form the native speaker used
    distractor: str      # the form a learner builds from the wrong stem
    lemma: str
    case: str            # Vabamorf tag, e.g. "sg in"
    case_et: str         # "seesütlev" — the name an examiner uses
    rule: str            # "case-form" | "negation" | "rection"
    why_ru: str
    topic: str           # curriculum topic id
    level: str | None
    source_id: str
    governor: str = ""   # the word whose rection is under test, for rection items

    @property
    def hint(self) -> str:
        """What the learner is told: which word, and which case to put it in.

        This is the whole reason an authentic sentence is safe to drill — name
        the case and the answer is forced, so nothing is being asserted about
        which case the sentence needed.
        """
        if self.governor:
            # For rection the case is the *question*, so naming it would give
            # the answer away. The governing word is the whole prompt.
            return f"{self.lemma} — {self.governor}?"
        return f"{self.lemma}, {self.case_et}"

    @property
    def label(self) -> str:
        """The half of `hint` that is not the word — what to produce.

        Every other generator gets this from `item.GradedItem`; this class
        predates the mixin and still carries its own copy of the whole surface,
        which is precisely the drift `eesti/item.py` was written to stop. It
        went unnoticed until the page needed the two halves apart and cloze
        items came back with the case missing.

        Not folded into the mixin here because `check` and `solution` also
        differ (`lower` against `casefold`, no sentence-initial capitalisation),
        and changing how an answer is graded does not belong in a layout fix.
        """
        return f"{self.governor}?" if self.governor else self.case_et


def sentences(
    conn: sqlite3.Connection,
    source_id: str = "selges-keeles",
    min_words: int = 5,
    max_words: int = 20,
) -> list[str]:
    """Sentences from the content store, at a length worth drilling.

    Under five words there is rarely enough context to place a case; over twenty
    the learner is parsing a paragraph rather than practising a form.
    """
    rows = conn.execute(
        "SELECT body FROM items WHERE source_id = ? AND body <> ''", (source_id,)
    ).fetchall()
    out: list[str] = []
    for row in rows:
        body = row[0] if not isinstance(row, sqlite3.Row) else row["body"]
        for sentence in split_sentences(body):
            sentence = sentence.strip()
            if not _usable(sentence):
                continue
            if min_words <= len(sentence.split()) <= max_words:
                out.append(sentence)
    return out


#: Selges keeles appends a glossary to some articles — `vöökiri = vöömuster` —
#: and the splitter carries the tail into the preceding sentence. 0.7 % of the
#: pool, which is small until one of them is the sentence a learner is asked to
#: write down from hearing it. Filtered here rather than at harvest time so it
#: applies to a `content.db` already pushed to a deployment.
_GLOSS = re.compile(r"\s=\s")


def _usable(sentence: str) -> bool:
    return not _GLOSS.search(sentence)


def naive_case_form(nominative: str, genitive: str, correct: str) -> str | None:
    """The form a learner builds from the nominative instead of the genitive stem.

    Estonian builds almost every case on the genitive stem, so the characteristic
    beginner error is attaching the ending to the citation form: `sõber` + `-s`
    gives `sõbers` where the language says `sõbras`. Recovering the ending by
    stripping the genitive off the correct form means we never have to hard-code
    a table of endings — and it returns None exactly when the genitive is not a
    prefix of the form, which is where this model of the error stops applying.
    """
    if not genitive or not correct.startswith(genitive):
        return None
    ending = correct[len(genitive):]
    if not ending:
        return None
    return nominative + ending


def _distractor(
    lemma: str, tag: str, correct: str, forms: dict[str, str]
) -> str | None:
    """The wrong answer, chosen to be the error the learner would actually make.

    Three cases, because the characteristic mistake differs:

    * **genitive** — the learner leaves the word in its citation form. Stripping
      the genitive off itself yields no ending, so the nominative-stem model has
      nothing to say here; the nominative *is* the error.
    * **partitive** — the documented weakness: genitive where partitive belongs,
      and the other way round. The contrast is the drill.
    * **everything else** — built on the nominative stem instead of the genitive
      one, which is why `gen-stem` is upstream of eleven topics.
    """
    if tag == "sg g":
        return lemma if lemma != correct else forms.get("partitive")
    if tag == "sg p":
        return forms.get("genitive")
    return naive_case_form(lemma, forms["genitive"], correct)


def _why(
    lemma: str, tag: str, correct: str, wrong: str, forms: dict[str, str]
) -> str:
    case_et, case_ru = CASES[tag]
    if tag == "sg g":
        return (
            f"**{case_et}** — {case_ru}. Словарная форма *{lemma}* здесь не "
            f"подходит: нужна основа генитива — **omastav** *{correct}*."
        )
    if tag == "sg p":
        return (
            f"**{case_et}** — {case_ru}. Здесь *{correct}*, а не **omastav** "
            f"*{wrong}*."
        )
    return (
        f"**{case_et}** — {case_ru}. Падеж строится от основы генитива — **omastav** "
        f"(*{forms['genitive']}*), а не от словарной формы: *{correct}*, "
        f"не *{wrong}*."
    )


def _unambiguous_lemma(surface: str, lemma: str, tag: str) -> bool:
    """The surface form must read back as this lemma in this case, and no other lemma.

    Naming the lemma in the prompt is what makes the answer unique, so a token
    that two different lemmas could produce cannot be used.
    """
    readings = _readings(surface)
    if (lemma, tag) not in readings:
        return False
    return len({lm for lm, _ in readings}) == 1


def _synthesises_back(lemma: str, tag: str, surface: str) -> bool:
    """Vabamorf must produce the attested form from the lemma and case.

    Where the corpus and the synthesiser disagree the item is dropped. That
    costs yield and buys the thing that matters: a grader that is right.
    """
    return surface in (synthesize(lemma, tag) or [])


def _clause_span(sentence: str, position: int) -> tuple[int, int]:
    """The clause containing a character offset, as (start, end)."""
    start, end = 0, len(sentence)
    for match in _CLAUSE_RE.finditer(sentence):
        if match.end() <= position:
            start = match.end()
        elif match.start() >= position:
            end = match.start()
            break
    return start, end


def _blank(sentence: str, start: int, end: int) -> str:
    return sentence[:start] + BLANK + sentence[end:]


def _hyphenated(sentence: str, start: int, end: int) -> bool:
    """Is this token glued to a neighbour by a hyphen?

    Blanking half of *"Selges keeles-žürii"* asks the learner to inflect a word
    that is not standing on its own, and the surviving fragment gives the answer
    away as often as it hides it.
    """
    # A two-character window, not one: the corpus writes *"Selges keeles
    # -žürii"* with a space before the hyphen, which a one-character check
    # walks straight past.
    return "-" in sentence[max(0, start - 2):start] + sentence[end:end + 2]


def _level_of(conn: sqlite3.Connection | None, lemma: str) -> str | None:
    if conn is None:
        return None
    row = conn.execute(
        "SELECT proficiency FROM words WHERE word = ?", (lemma,)
    ).fetchone()
    return row[0] if row else None


#: CEFR levels above the ones this app targets. A word the word list *says* is
#: B2 is not what an A2 learner should be inflecting.
_ABOVE = ("B2", "C1", "C2")


def _above_level(level: str | None, levels: tuple[str, ...]) -> bool:
    """Is this word's tag a claim that it is too hard?

    The asymmetry matters, and it is the same one the reading library uses: a
    tag of B2 is evidence, absence of a tag is not. Only 6.2 % of the 160 316
    lemmas carry a CEFR tag at all, so treating "untagged" as "too hard" would
    throw away 36 % of the corpus targets for no reason anyone could defend.

    Measured over 272 generated `osastav` items: 57 % tagged A1-B1, 36 %
    untagged, and 7 % tagged B2 or C1 -- `hooldustöö`, `riigivisiit`. It is
    those 7 % this drops.
    """
    if level is None:
        return False
    return level in _ABOVE and level not in levels


def _ease(conn: sqlite3.Connection | None, tokens) -> float:
    """Share of a sentence's content words that the word list calls A1 or A2.

    `difficulty.score` is the same measurement and says in its own docstring
    that ordering is what it is for. It is not reused directly because it runs
    a second Vabamorf pass -- 14.3 s over the 2 038-sentence pool, inside a
    request the learner is waiting on. Here the analysis is already in hand, so
    the same number costs one indexed query.

    Ordering, never a threshold. The scale is uncalibrated -- that is the whole
    lesson of `eesti/difficulty.py` -- so this decides which authentic sentence
    comes first, and nothing at all about what level it is.
    """
    if conn is None:
        return 0.0
    lemmas = {t.lemma for t in tokens if t.pos in ("S", "V", "A")}
    if not lemmas:
        return 0.0
    marks = ",".join("?" * len(lemmas))
    row = conn.execute(
        f"""SELECT COUNT(*) FROM words
            WHERE word IN ({marks}) AND proficiency IN ('A1', 'A2')""",
        list(lemmas),
    ).fetchone()
    return (row[0] or 0) / len(lemmas)


#: How many candidates to gather before keeping the easiest `count`.
#:
#: The pool was shuffled and the first `count` hits were shipped, so a practice
#: set was a random sample of authentic sentences -- which is how "Neid pakkuvad
#: ettevõted peavad esitama oma pakkumised enne jaanuari ____" reached an A1
#: topic. Three times is enough to have a real choice without walking the whole
#: corpus on every request.
OVERSAMPLE = 3


def case_clozes(
    sents: list[str],
    topics: tuple[str, ...] | None = None,
    words: sqlite3.Connection | None = None,
    count: int = 10,
    seed: int | None = None,
    source_id: str = "selges-keeles",
    require_contrast: bool = True,
    only: frozenset[str] | None = None,
    levels: tuple[str, ...] = LEVELS,
) -> list[Cloze]:
    """Case-production items: the sentence is real, the case is named, produce the form.

    The prompt gives the lemma and the case, so the answer is forced by
    morphology alone and nothing is being claimed about which case the sentence
    *needed*. That is what makes an authentic sentence safe to drill.

    `levels` gates the **target word**, and candidates are ordered so the
    easiest sentences are drilled first. Both used to be missing: `levels` was
    threaded from `items_for` into this module and then dropped, taking effect
    only when a theme happened to be chosen, so the default run of every corpus
    topic drilled B2 nouns inside newspaper prose.
    """
    wanted: set[str] = set()
    for topic in topics or tuple(TOPIC_CASES):
        wanted |= set(TOPIC_CASES.get(topic, ()))
    by_case = {tag: topic for topic, tags in TOPIC_CASES.items() for tag in tags}

    rng = random.Random(seed)
    pool = list(sents)
    rng.shuffle(pool)

    out: list[tuple[float, Cloze]] = []
    seen: set[tuple[str, str]] = set()
    for sentence in pool:
        if len(out) >= count * OVERSAMPLE:
            break
        tokens = analyze(sentence)
        ease = _ease(words, tokens)
        for token in tokens:
            if token.pos != "S" or token.form not in wanted:
                continue
            if only is not None and token.lemma not in only:
                continue
            level = _level_of(words, token.lemma)
            if _above_level(level, levels):
                continue
            if (token.lemma, token.form) in seen:
                continue
            if not _WORD_RE.search(token.text):
                continue
            if _hyphenated(sentence, token.start, token.end):
                continue

            forms = case_forms(token.lemma)
            if not forms:
                continue
            if not _unambiguous_lemma(token.text, token.lemma, token.form):
                continue
            if not _synthesises_back(token.lemma, token.form, token.text):
                continue

            wrong = _distractor(token.lemma, token.form, token.text, forms)
            if wrong is None or (require_contrast and wrong == token.text):
                continue

            case_et, case_ru = CASES[token.form]
            out.append((ease, Cloze(
                    prompt=_blank(sentence, token.start, token.end),
                    answer=token.text,
                    distractor=wrong,
                    lemma=token.lemma,
                    case=token.form,
                    case_et=case_et,
                    rule="case-form",
                    why_ru=_why(token.lemma, token.form, token.text, wrong, forms),
                    topic=by_case[token.form],
                    level=level,
                    source_id=source_id,
                ))
            )
            seen.add((token.lemma, token.form))
            break  # one item per sentence, so a text is not drilled to death

    # Easiest first. `sorted` is stable, so within one ease score the shuffled
    # order survives and a set is not the same ten sentences every time.
    out.sort(key=lambda pair: -pair[0])
    return [item for _, item in out[:count]]


def negation_clozes(
    sents: list[str],
    words: sqlite3.Connection | None = None,
    count: int = 10,
    seed: int | None = None,
    source_id: str = "selges-keeles",
    levels: tuple[str, ...] = LEVELS,
) -> list[Cloze]:
    """The one object-case rule a corpus sentence can settle on its own.

    Under negation Estonian takes the partitive without exception, so no aspect
    judgement is needed and the genitive really is wrong. The completed/ongoing
    contrast is *not* generated from the corpus — both cases are often licit
    there, and marking a licit answer wrong teaches a rule that does not exist.
    """
    rng = random.Random(seed)
    pool = list(sents)
    rng.shuffle(pool)

    out: list[tuple[float, Cloze]] = []
    seen: set[str] = set()
    for sentence in pool:
        if len(out) >= count * OVERSAMPLE:
            break
        tokens = analyze(sentence)
        ease = _ease(words, tokens)
        negators = [
            t for t in tokens
            if t.lemma in NEGATORS or t.text.lower() in _CONTRACTED
        ]
        if not negators:
            continue

        for token in tokens:
            if token.pos != "S" or token.form != "sg p" or token.lemma in seen:
                continue
            level = _level_of(words, token.lemma)
            if _above_level(level, levels):
                continue
            # The negator must govern *this* noun: same clause, and before it,
            # which is where Estonian puts it.
            lo, hi = _clause_span(sentence, token.start)
            if not any(lo <= n.start < token.start and n.end <= hi for n in negators):
                continue
            forms = case_forms(token.lemma)
            if not forms or forms["genitive"] == forms["partitive"]:
                continue
            if not _unambiguous_lemma(token.text, token.lemma, "sg p"):
                continue
            if _hyphenated(sentence, token.start, token.end):
                continue
            if not _synthesises_back(token.lemma, "sg p", token.text):
                continue

            out.append((ease, Cloze(
                    prompt=_blank(sentence, token.start, token.end),
                    answer=token.text,
                    distractor=forms["genitive"],
                    lemma=token.lemma,
                    case="sg p",
                    case_et="osastav",
                    rule="negation",
                    why_ru=(
                        "Отрицание всегда требует **osastav** — исключений нет. "
                        f"*{token.text}*, не *{forms['genitive']}*."
                    ),
                    topic="obj-case",
                    level=level,
                    source_id=source_id,
                ))
            )
            seen.add(token.lemma)
            break

    out.sort(key=lambda pair: -pair[0])
    return [item for _, item in out[:count]]


# ---------------------------------------------------------------------------
# Rection
# ---------------------------------------------------------------------------
#
# These are generated from a frame rather than from the corpus, which inverts
# the choice made everywhere else in this module — deliberately. A corpus is
# authoritative about case *forms*, because morphology is not something a
# journalist gets wrong. It is **not** authoritative about case *choice* after
# a verb, because that is precisely what people get wrong: searching the 2 073
# harvested sentences for these verbs returned three hits, and one of them was
# *"süsteem põhineb kaartidele"* — the exact error EKK stars under `põhinema`,
# in published simplified news. Mining that sentence would have taught the
# mistake as the answer.

# Semantically bleached fillers, split only by what the frame itself says: a
# `keda`/`kelle` frame wants a person, a `mida`/`mille` frame wants a thing.
# No per-verb pool to maintain — abstract nouns fit all of these verbs.
_THINGS = ("olukord", "plaan", "otsus", "süsteem", "muudatus", "tulemus", "seadus")
_PEOPLE = ("klient", "elanik", "õpilane", "töötaja", "naaber")

# Verbs that cannot take a personal subject. Everything else defaults to "Ta",
# which is the only agreement-free pronoun in the language. Listing five
# exceptions by hand beats generating "Ta põhineb otsusel".
_IMPERSONAL = frozenset({"põhinema", "rajanema", "baseeruma", "kaasnema", "vastanduma"})


def _finite(lemma: str) -> str | None:
    """Third person singular present — the tag Vabamorf calls `b`."""
    forms = synthesize(lemma, "b") or []
    return forms[0] if forms else None


def _in_case(lemma: str, tag: str) -> str | None:
    """Synthesise and round-trip, the same gate every other item passes."""
    for candidate in synthesize(lemma, tag) or []:
        if (lemma, tag) in _readings(candidate):
            return candidate
    return None


def rection_clozes(
    rections: list,
    words: sqlite3.Connection | None = None,
    count: int = 10,
    seed: int | None = None,
) -> list[Cloze]:
    """Which case does this word govern? The contrast comes from EKK, not from me.

    Both halves are the handbook's: `kohanema` takes *millega*, and EKK stars
    *millele* as what people write instead. So the distractor is a documented
    error rather than a plausible-looking decoy — the same standard the verb
    drills hold themselves to.
    """
    rng = random.Random(seed)
    out: list[Cloze] = []
    for rection in rng.sample(list(rections), k=len(rections)):
        if len(out) >= count:
            break
        person = rection.correct_frame.startswith(("kelle", "keda"))
        noun = rng.choice(_PEOPLE if person else _THINGS)

        answer = _in_case(noun, rection.correct_case)
        wrong = _in_case(noun, rection.wrong_case)
        if not answer or not wrong or answer == wrong:
            continue

        head = rection.headword
        if head.endswith("ma"):
            verb = _finite(head)
            if not verb:
                continue
            subject = "See" if head in _IMPERSONAL else "Ta"
            prompt = f"{subject} {verb} {BLANK}."
        else:
            prompt = f"See on {BLANK} {head}."

        case_et, case_ru = CASES.get(rection.correct_case, (rection.correct_case, ""))
        wrong_et = CASES.get(rection.wrong_case, (rection.wrong_case, ""))[0]
        out.append(
            Cloze(
                prompt=prompt,
                answer=answer,
                distractor=wrong,
                lemma=noun,
                case=rection.correct_case,
                case_et=case_et,
                rule="rection",
                why_ru=(
                    f"**{head}** требует падежа *{rection.correct_frame}* "
                    f"({case_et}), а не *{rection.wrong_frame}* ({wrong_et}). "
                    f"EKK отмечает это как частую ошибку."
                ),
                topic="rektsioon",
                level=_level_of(words, noun),
                source_id="ekk",
                governor=head,
            )
        )
    return out
