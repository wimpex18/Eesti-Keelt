"""Verb government (rektsioon), from the list EKI keeps of the ones people get wrong.

Rection is the **second-largest error class** in the EVKK learner corpus — 5 170
annotated marks, 10 % of everything, against object case's 1.3 %. It is also the
error a Russian speaker is structurally set up to make, because the Estonian case
and the Russian preposition rarely line up: *mõtlema **millele*** where Russian
says *думать **о чём***.

## Why not fetch this from a dictionary

`providers/sonapi.py` returns the rection of any single verb, and the obvious
move is to walk the ~130 indexed A1-B1 verbs and collect them. That module says,
in its own docstring, single lookups only and deliberately no bulk helper —
Sõnaveeb's maintainers ask not to be batch-requested, and reinterpreting my own
constraint the moment it becomes inconvenient is how that kind of rule dies. So
sonapi stays interactive: it enriches a word the learner is actually looking at.

The bulk source is better anyway. **EKK SÜ 64 is titled "Rektsioone, milles
sageli eksitakse"** — *rections that are often got wrong* — and it is a table of
exactly that: headword, the correct case frame, and, starred, the wrong one.
An authority's own error list, on one page, fetched once.

That is a considerably better drill source than a dictionary dump, because the
wrong answer does not have to be invented. `kohanema` governs *millega*, and EKK
records that people write *millele*; the drill is that contrast, and both halves
come from the handbook rather than from me.

## What is stored, and what is not

Stored: **headword, correct frame, marked wrong frame** — lexical facts about
which case a verb takes. Not stored: EKK's example sentences, which are the
handbook's own prose. Drills are built over the harvested corpus instead, so
nothing is reproduced and the sentences are at the learner's level rather than
the handbook's.

## The honest size of it

62 entries, 30 with a marked error, and **11 of those 30 are A1-B1** — the rest
are B2 vocabulary like *baseeruma* and *proportsionaalne*, which are filed and
filtered out rather than drilled at the wrong level. Eleven is a small set. It is
also eleven contrasts that a state-published grammar says learners get wrong, for
the error class the learner corpus ranks second, which is a better place to start
than a hundred rections nobody struggles with.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass

from .grammar import EKK_BASE

# SÜ 64 lives on the syntax chapter's "LAUSE EHITUS" page.
SOURCE_URL = f"{EKK_BASE}?p=5&p1=2"
SECTION = "Rektsioone, milles sageli eksitakse"
TIMEOUT = 60.0
RETRIES = 3
UA = "Eesti-Keelt/0.1 (personal language-learning tool)"

# EKK writes rections as interrogative pronouns — the way an Estonian teacher
# says them out loud, and the way the exam will. Each maps to one Vabamorf case.
FRAME_CASES: dict[str, str] = {
    "mida": "sg p", "keda": "sg p",
    "mille": "sg g", "kelle": "sg g", "mis": "sg n",
    "millega": "sg kom", "kellega": "sg kom",
    "millele": "sg all", "kellele": "sg all",
    "millel": "sg ad", "kellel": "sg ad",
    "millelt": "sg abl", "kellelt": "sg abl",
    "millest": "sg el", "kellest": "sg el",
    "milles": "sg in", "kelles": "sg in",
    "millesse": "sg ill", "kellesse": "sg ill",
    "milleks": "sg tr", "kelleks": "sg tr",
    "milleni": "sg ter",
    "milleta": "sg ab",
    "millena": "sg es", "kellena": "sg es",
}

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_FRAME_RE = re.compile(r"\b([a-zõäöüA-ZÕÄÖÜ]+)\b")


@dataclass(frozen=True)
class Rection:
    """One verb (or adjective), the case it governs, and the case people use instead."""

    headword: str
    correct_frame: str   # "millega" — as EKK writes it
    wrong_frame: str     # "millele" — as EKK stars it
    correct_case: str    # Vabamorf tag
    wrong_case: str

    @property
    def drillable(self) -> bool:
        return self.correct_case != self.wrong_case


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(_TAG_RE.sub(" ", fragment))).strip()


def _frames(text: str) -> list[str]:
    """Every case frame in a fragment, in order, deduplicated."""
    out: list[str] = []
    for word in _FRAME_RE.findall(text):
        low = word.lower()
        if low in FRAME_CASES and low not in out:
            out.append(low)
    return out


def parse(page: str) -> list[Rection]:
    """Rections with a marked error, from EKK's own table.

    Entries whose frame is not a case — `millal` (when), `mis ajast` (from when),
    or a postposition like `kelle vastu` — are dropped rather than forced into a
    case slot. They are real rules, but they are not a case contrast, and a drill
    that pretends otherwise would be teaching the wrong thing.
    """
    start = page.rfind(SECTION)
    if start < 0:
        return []
    end = page.find("Üldlaiend", start)
    table = page[start : end if end > 0 else len(page)]

    out: list[Rection] = []
    seen: set[str] = set()
    for row in _ROW_RE.findall(table):
        cells = [_clean(c) for c in _CELL_RE.findall(row)]
        if len(cells) < 2:
            continue
        headword = cells[0].split("'")[0].split("‘")[0].strip(" /,")
        headword = headword.split()[0] if headword else ""
        frames = cells[1]
        if not headword or "*" not in frames or headword in seen:
            continue

        correct_text, _, rest = frames.partition("(")
        starred, _, tail = rest.partition(")")

        # Exactly one correct frame, or the entry is not a clean contrast:
        # EKK writes `sarnane mille/millega (*millele)`, where two cases are
        # right and a drill accepting one of them marks the other wrong.
        correct = _frames(correct_text)
        wrong = _frames(starred)
        if len(correct) != 1 or len(wrong) != 1:
            continue

        # The tail can license the very case the star rejects: `kindel milles
        # (*millele) kellele ~ kelle peale` stars the allative for things and
        # then allows it for people. Same case on both sides is a contradiction,
        # not a contrast.
        wrong_case = FRAME_CASES[wrong[0]]
        if any(FRAME_CASES[f] == wrong_case for f in _frames(tail)):
            continue

        rection = Rection(
            headword=headword,
            correct_frame=correct[0],
            wrong_frame=wrong[0],
            correct_case=FRAME_CASES[correct[0]],
            wrong_case=wrong_case,
        )
        if rection.drillable:
            out.append(rection)
            seen.add(headword)
    return out


def fetch(cache=None) -> list[Rection]:
    """One request, cached. The handbook is a book; it does not change weekly."""
    from pathlib import Path

    from . import net

    if cache is not None and Path(cache).exists():
        return parse(Path(cache).read_text(encoding="utf-8"))

    page = net.get(SOURCE_URL, "EKK SÜ 64", timeout=TIMEOUT,
                   retries=RETRIES, ua=UA)

    if cache is not None:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        Path(cache).write_text(page, encoding="utf-8")
    return parse(page)


SCHEMA = """
CREATE TABLE IF NOT EXISTS rections (
    headword      TEXT PRIMARY KEY,
    correct_frame TEXT NOT NULL,
    wrong_frame   TEXT NOT NULL,
    correct_case  TEXT NOT NULL,
    wrong_case    TEXT NOT NULL
);
"""


def load(conn) -> list[Rection]:
    """Read the stored table. **No network** — that is the whole point.

    `fetch` belongs to a deliberate, one-time `cli rections` run. Calling it
    from a lesson made a practice session depend on EKI being reachable, and
    CI proved the point by getting a 403 from a GitHub runner: a drill that
    cannot run because someone else's server is having a bad minute is exactly
    what this project claims not to build.
    """
    conn.executescript(SCHEMA)
    return [
        Rection(r[0], r[1], r[2], r[3], r[4])
        for r in conn.execute(
            "SELECT headword, correct_frame, wrong_frame, correct_case, wrong_case"
            " FROM rections ORDER BY headword"
        )
    ]


def store(conn, rections: list[Rection]) -> int:
    conn.executescript(SCHEMA)
    with conn:
        conn.execute("DELETE FROM rections")
        conn.executemany(
            "INSERT INTO rections"
            " (headword,correct_frame,wrong_frame,correct_case,wrong_case)"
            " VALUES (?,?,?,?,?)",
            [
                (r.headword, r.correct_frame, r.wrong_frame,
                 r.correct_case, r.wrong_case)
                for r in rections
            ],
        )
    return len(rections)


def at_levels(conn, rections: list[Rection], levels: tuple[str, ...]) -> list[Rection]:
    """Keep the rections whose headword is at the learner's level.

    Two thirds of EKK's list is B2 vocabulary. Drilling *baseeruma* at A2 teaches
    a case frame attached to a word the learner will not meet, which is effort
    spent on the wrong half of the problem.
    """
    if not rections:
        return []
    marks = ",".join("?" * len(rections))
    known = {
        row[0]
        for row in conn.execute(
            f"SELECT word FROM words WHERE proficiency IN "
            f"({','.join('?' * len(levels))}) AND word IN ({marks})",
            (*levels, *(r.headword for r in rections)),
        )
    }
    return [r for r in rections if r.headword in known]


# ---------------------------------------------------------------------------
# Checking free writing: EVKK's `&err-gov`
# ---------------------------------------------------------------------------
#
# Rection is the second-largest class in the learner corpus — 5 170 marks
# against object case's 653 — and until now this module could only *drill* it.
#
# **What makes this checkable at all.** General rection checking needs valency:
# which noun phrase is this verb's complement, and is its case one the verb
# permits. That is syntax, and this project has morphology — the same wall
# `object_case_candidates` refuses to climb.
#
# EKK SÜ 64 sidesteps it by being a list of *specific attested confusions*. It
# does not say "kohanema takes the comitative"; it says **people write
# `millele` where `millega` belongs**. So the question here is not "is this
# case valid" but "is this the exact case EKK records as the mistake" — which
# is a lookup, not an analysis.
#
# Three conditions, all of which must hold, because a checker that invents
# errors teaches that correct Estonian is wrong:
#
#   1. the headword is one of EKK's 23 attested contrasts;
#   2. a word **in its own clause** stands in the starred wrong case;
#   3. **nothing** in that clause stands in the correct case — if the right
#      complement is there too, the flagged word is something else's.
#
#: Clause boundaries, which are where a complement search has to stop.
#:
#: Estonian marks subordinate clauses with a comma far more reliably than
#: English does, so this is a real boundary rather than a guess. Without it,
#: "Ma kirjutasin sõbrale, et süsteem põhineb loogikal" flags `sõbrale` —
#: allative, `põhinema`'s starred wrong case — from the other side of a comma,
#: while the actual complement `loogikal` sits correctly beside the verb.
_CLAUSE_SPLIT = ";:,"


@dataclass(frozen=True)
class Misgovernment:
    """A verb from EKK's list, with its complement in the case EKK stars."""

    headword: str
    #: The learner's word, and what it should have been.
    wrong: str
    correct: str
    correct_frame: str   # "millega", for the explanation
    wrong_frame: str
    start: int
    end: int


def _clauses(tokens: list) -> list[list]:
    """Split analysed tokens at clause punctuation."""
    out, current = [], []
    for token in tokens:
        if token.pos == "Z" and token.text in _CLAUSE_SPLIT:
            if current:
                out.append(current)
            current = []
        else:
            current.append(token)
    if current:
        out.append(current)
    return out


def _case_of(form: str | None) -> str:
    """The case, without the number.

    EKK writes its frames as singular question words — `millega`, `millele` —
    so `FRAME_CASES` stores `sg kom` and `sg all`. A learner writes about more
    than one thing as readily as one: `põhineb faktidele` is `pl all`, and
    comparing whole tags meant every plural complement went unchecked. **The
    case is the claim; the number is the learner's business.**
    """
    return (form or "").split(" ")[-1]


def _number_of(form: str | None) -> str:
    return (form or "sg ").split(" ")[0] or "sg"


#: Parts of speech that agree with a noun inside its phrase.
#:
#: `kohanema uuele olukorrale` is one complement, not two candidates — the
#: adjective is in the allative because the noun is. Counting them separately
#: made every modified noun phrase look ambiguous and skipped it, which is how
#: the first version of this check fired on nothing at all.
_MODIFIERS = frozenset({"A", "P", "N", "O", "G"})


def errors(text: str, rections: list[Rection]) -> list[Misgovernment]:
    """Attested rection confusions in free writing, with the case that belongs.

    `rections` is passed in rather than loaded here so the caller owns the
    database handle — the same reason `library` takes a connection.
    """
    from .morph import analyze, split_sentences

    by_head = {r.headword: r for r in rections if r.drillable}
    if not by_head:
        return []

    found: list[Misgovernment] = []
    for sentence in split_sentences(text) or [text]:
        offset = text.find(sentence)
        for clause in _clauses(analyze(sentence)):
            lemmas = {t.lemma for t in clause}
            for headword, rule in by_head.items():
                if headword not in lemmas:
                    continue
                right = _case_of(rule.correct_case)
                starred = _case_of(rule.wrong_case)
                # Condition 3: the right complement is not already here.
                if any(_case_of(t.form) == right for t in clause):
                    continue

                candidates = [t for t in clause if _case_of(t.form) == starred]
                # The head of the phrase is the noun; anything agreeing with it
                # is part of the same complement, not a rival one.
                nouns = [t for t in candidates if t.pos == "S"]
                others = [t for t in candidates if t.pos not in _MODIFIERS | {"S"}]
                # One noun phrase, or there is no telling which is meant.
                if len(nouns) != 1 or others:
                    continue
                token = nouns[0]
                fixed = _synthesize(
                    token.lemma, f"{_number_of(token.form)} {right}")
                if not fixed:
                    continue
                at = sentence.find(token.text)
                found.append(Misgovernment(
                    headword=headword,
                    wrong=token.text,
                    correct=fixed,
                    correct_frame=rule.correct_frame,
                    wrong_frame=rule.wrong_frame,
                    start=offset + at if offset >= 0 and at >= 0 else -1,
                    end=offset + at + len(token.text) if offset >= 0 and at >= 0 else -1,
                ))
    return found


def _synthesize(lemma: str, case: str) -> str:
    """The complement in the case the handbook says belongs there.

    Vabamorf, so the suggestion is generated by the same call that produces
    every drill answer rather than assembled from an ending table.
    """
    from estnltk.vabamorf.morf import synthesize

    forms = synthesize(lemma, case, "S") or []
    return forms[0] if forms else ""
