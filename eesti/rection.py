"""Verb government (rektsioon), from EKK SÜ 65: "Rektsioone, milles sageli eksitakse".

Rection is a large learner error class, and a natural one for a Russian speaker
(*mõtlema millele* vs *думать о чём*). EKK's table lists the headword, the
correct case frame and, starred, the frame people write instead — so both the
answer and the distractor come from the handbook.

Fetched once by `cli rections` (not from Sõnaveeb, which must not be batched).
Stored: headword, correct frame, starred wrong frame. Not stored: EKK's example
sentences. Only headwords at the learner's level are drilled.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass

from .grammar import EKK_BASE

# SÜ 65 lives on the syntax chapter's "LAUSE EHITUS" page.
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
    """Rections with a marked error, from EKK's table. Frames that are not a case
    (`millal`, postposition phrases) are dropped.
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

        # The tail can license the starred case for another argument; the same case on
        # both sides is a contradiction, not a contrast.
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

    page = net.get(SOURCE_URL, "EKK SÜ 65", timeout=TIMEOUT,
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
    """Read the stored table, with no network; `fetch` belongs to `cli rections`."""
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
    """Keep the rections whose headword is at the learner's level; most of EKK's list
    is B2 vocabulary.
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
# General rection checking needs valency (syntax). SÜ 65 lists specific attested
# confusions, so this is a lookup. All three must hold:
#
#   1. the headword is one of EKK's attested contrasts;
#   2. a word in its own clause stands in the starred wrong case;
#   3. nothing in that clause stands in the correct case.
#
# Clause boundaries, where a complement search stops (Estonian reliably marks
# subordinate clauses with a comma).
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
    """The case without the number: EKK's frames are singular, but a plural complement
    is checked the same way.
    """
    return (form or "").split(" ")[-1]


def _number_of(form: str | None) -> str:
    return (form or "sg ").split(" ")[0] or "sg"


#: Parts of speech that agree with a noun inside its phrase, so `uuele olukorrale`
#: counts as one complement.
_MODIFIERS = frozenset({"A", "P", "N", "O", "G"})


def errors(text: str, rections: list[Rection]) -> list[Misgovernment]:
    """Attested rection confusions in free writing, with the case that belongs.
    `rections` is passed in so the caller owns the database handle.
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
    """The complement in the correct case, synthesised by Vabamorf."""
    from estnltk.vabamorf.morf import synthesize

    forms = synthesize(lemma, case, "S") or []
    return forms[0] if forms else ""
