"""Drills built from sentences Estonians actually wrote.

Blanking a word in a harvested sentence gives unlimited variety and an answer
that is correct because a native wrote it — but only where the answer is
**forced**:

1. **The prompt names the case** (*"Ma elan ____ (Tallinn, seesütlev)"*):
   morphology decides the form, and nothing is claimed about which case the
   sentence needed.
2. **A trigger makes the case obligatory:** negation takes the partitive
   without exception. Genitive-vs-partitive choices are generated only there;
   elsewhere both are often licit (telicity is semantics).

**Distractors are the real error:** the same case built on the nominative stem
instead of the genitive stem (`sõber` + `-s` → `sõbers`, not `sõbras`). No
contrast, no item.

**Gates before an item ships:** an unambiguous lemma; Vabamorf's synthesis of
`(lemma, case)` reproduces the attested form exactly; answer and distractor
differ.
"""

from __future__ import annotations

import random
import re
import sqlite3
from dataclasses import dataclass

from estnltk.vabamorf.morf import synthesize

from .config import LEVELS
# `BLANK` is re-exported, not redefined. `item.BLANK` is the one definition; a
# second literal here is the same duplication as the four private `_TAG_RE`s
# that gave one line of input three different answers.
from .item import BLANK, GradedItem
from .morph import _readings, analyze, case_forms, split_sentences

# Vabamorf case tags -> Estonian name and Russian gloss. Nominative (the prompt's
# citation form) and the short illative (optional) are excluded.
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

# Negation scopes over its own clause: split on punctuation and clause-introducing
# words, erring towards dropping items.
_CLAUSE_RE = re.compile(
    r"[,;:—–]|\b(?:kui|et|sest|kuid|aga|siis|mis|mida|kes|keda|kuna|ehkki|"
    r"kuigi|ning|või)\b",
    re.IGNORECASE,
)

# Vabamorf hands back punctuation as tokens of its own. A candidate with no
# word character in it is one of those, and blanking it asks the learner to
# inflect a comma.
_WORD_RE = re.compile(r"\w", re.UNICODE)


@dataclass(frozen=True)
class Cloze(GradedItem):
    """One corpus item, graded through `item.GradedItem`. `hint` is overridden because
    for rection the case is the question.
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
        """What the learner is told: which word, and which case to put it in."""
        if self.governor:
            # For rection the case is the *question*, so naming it would give
            # the answer away. The governing word is the whole prompt.
            return f"{self.lemma} — {self.governor}?"
        return f"{self.lemma}, {self.case_et}"

    @property
    def label(self) -> str:
        """The half of `hint` that is not the word — what to produce."""
        return f"{self.governor}?" if self.governor else self.case_et


def sentences(
    conn: sqlite3.Connection,
    source_id: str = "selges-keeles",
    min_words: int = 5,
    max_words: int = 20,
) -> list[str]:
    """Sentences from the content store of 5–20 words: enough context to place a case,
    short enough not to become parsing practice.
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


#: Selges keeles glossary tails (`vöökiri = vöömuster`) glued onto a sentence;
#: filtered at read time so already-pushed corpora are covered.
_GLOSS = re.compile(r"\s=\s")


def _usable(sentence: str) -> bool:
    return not _GLOSS.search(sentence)


def naive_case_form(nominative: str, genitive: str, correct: str) -> str | None:
    """The form a learner builds from the nominative instead of the genitive stem.

    Recovers the ending by stripping the genitive off the correct form, so no
    ending table is needed; None when the genitive is not a prefix of the form.
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

    - **genitive** — the citation form is the error;
    - **partitive** — the genitive/partitive contrast itself;
    - **everything else** — built on the nominative stem.
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
    """The surface form must read back as this lemma in this case, and no other lemma."""
    readings = _readings(surface)
    if (lemma, tag) not in readings:
        return False
    return len({lm for lm, _ in readings}) == 1


def _synthesises_back(lemma: str, tag: str, surface: str) -> bool:
    """Vabamorf must produce the attested form from the lemma and case; otherwise the
    item is dropped.
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
    """Is this token glued to a neighbour by a hyphen? Such fragments are not blanked."""
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

    A B2/C1 tag is evidence; no tag is not (most lemmas carry none), so only words
    tagged above the target levels are dropped.
    """
    if level is None:
        return False
    return level in _ABOVE and level not in levels


def _ease(conn: sqlite3.Connection | None, tokens) -> float:
    """Share of a sentence's content words that the word list calls A1 or A2.

    The same measure as `difficulty.score`, but computed from the analysis already
    in hand instead of a second Vabamorf pass. Used for ordering only, never as a
    level threshold.
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


#: Gather this many times `count` candidates, then keep the easiest.
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

    `levels` gates the target word, and candidates are ordered easiest first.
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

            case_et = CASES[token.form][0]
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
    """The one object-case rule a corpus sentence can settle on its own: negation
    takes the partitive without exception.
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
# Generated from frames, not the corpus: published text is reliable about case
# forms but not about case choice after a verb, which is exactly the error being
# taught.

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
    """Which case does this word govern? Both the right case and the distractor come
    from EKK SÜ 64's list of attested confusions.
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

        case_et = CASES.get(rection.correct_case, (rection.correct_case, ""))[0]
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
