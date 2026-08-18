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
import time
import urllib.request
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

    if cache is not None and Path(cache).exists():
        return parse(Path(cache).read_text(encoding="utf-8"))

    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": UA})
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                page = resp.read().decode("utf-8", errors="replace")
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"EKK SÜ 64 unreachable: {last}")

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
