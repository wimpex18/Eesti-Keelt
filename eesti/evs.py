"""*Eesti-vene sõnaraamat* — Russian for an Estonian word, without a network call.

## The gap this fills

`gloss.py` gets Russian from Sõnaveeb, one live request per word, capped by a
daily budget and never in bulk. `data/seed_glossary.tsv` covers the 294 words
drills use most. Everything else a learner clicks while reading had no Russian
until Sõnaveeb was asked — and none at all offline, over budget, or with
Sõnaveeb down.

EKI publish the Estonian–Russian dictionary for download under CC BY 4.0:
70 882 articles, 60 610 lemmas with at least one usable Russian translation
(measured 2026-09-13 on `evs_EKI_CCBY40.xml`). So the Russian a word card needs
is a file, not a request.

## What is kept

Headword, part of speech, and at most `MAX_RUSSIAN` translations. Not the
Russian inflection notes, aspect pairs, government (`vrek`) or the translated
example phrases — a word card is a reminder, and Sõnaveeb is one link away for
the rest. Translations labelled archaic (`van`) are dropped: a learner at A2
should not meet `благой` as the meaning of `hea`.

## Senses before synonyms

`iga` is two articles — an age, and "every" — and the first sense of the first
already has four Russian words. Kept in file order, the card's three slots
would all say "age". So the order is breadth-first: the first translation of
every sense, across homonyms, then the second of each, and so on.

## Where it lives

`evs_gloss` in the words database, beside `psv_gloss` and for the same reason:
reference data, identical for everybody, and `vocab.db` is replaced whole by a
state-snapshot restore. It never writes `word_gloss` — Sõnaveeb's answers stay
Sõnaveeb's — so the preference between the two is stated where they are read,
in `api/grammar.py`: **offline EVS first, live Sõnaveeb second.**

The file's shape is not its schema's; `ekixml` has what was measured.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import ekixml

#: A word card shows three; five leaves the drill glosses room without turning
#: a reminder into an entry.
MAX_RUSSIAN = 5

#: Same separator as `gloss.py` and `psv.py`.
SEP = "\x1f"

#: EKI's style label for an obsolete translation.
ARCHAIC = "van"


@dataclass(frozen=True)
class Entry:
    lemma: str
    pos: str | None
    russian: tuple[str, ...]


def _senses(article) -> list[list[str]]:
    """Russian alternatives per sense, in order, archaic ones dropped."""
    senses = []
    for tg in article.iter("tg"):
        words = []
        for xp in tg.findall("xp"):
            if xp.get(ekixml.XML_LANG) != "ru":
                continue
            for xg in xp.findall("xg"):
                if any(ekixml.text(s) == ARCHAIC for s in xg.findall("s")):
                    continue
                word = ekixml.russian(xg.find("x"))
                # `_` is EVS saying "no single-word Russian; see the phrases".
                if word and word != "_":
                    words.append(word)
        if words:
            senses.append(words)
    return senses


def _breadth_first(senses: list[list[str]]) -> tuple[str, ...]:
    out: list[str] = []
    depth = 0
    while len(out) < MAX_RUSSIAN and any(depth < len(s) for s in senses):
        for words in senses:
            if depth < len(words) and words[depth] not in out:
                out.append(words[depth])
                if len(out) == MAX_RUSSIAN:
                    break
        depth += 1
    return tuple(out)


def parse(path: Path | str) -> list[Entry]:
    """One entry per lemma, homonyms merged, with at least one translation."""
    senses: dict[str, list[list[str]]] = {}
    pos: dict[str, str | None] = {}
    for article in ekixml.articles(path):
        lemma = ekixml.headword(article)
        if not lemma:
            continue
        found = _senses(article)
        if not found:
            continue
        senses.setdefault(lemma, []).extend(found)
        if lemma not in pos:
            first = article.find("P/mg/sl")
            pos[lemma] = ekixml.text(first) or None
    return [Entry(lemma, pos[lemma], _breadth_first(s)) for lemma, s in senses.items()]


SCHEMA = """
-- EKI's Estonian-Russian dictionary, in the words database: reference data.
CREATE TABLE IF NOT EXISTS evs_gloss (
    lemma   TEXT PRIMARY KEY,
    pos     TEXT,
    russian TEXT NOT NULL      -- \x1f-joined, like `word_gloss.russian`
);
"""


def store(conn: sqlite3.Connection, entries: list[Entry]) -> dict[str, int]:
    """Replace the table's contents with `entries`. Idempotent."""
    conn.executescript(SCHEMA)
    with conn:
        conn.execute("DELETE FROM evs_gloss")
        conn.executemany(
            "INSERT INTO evs_gloss (lemma, pos, russian) VALUES (?,?,?)",
            [(e.lemma, e.pos, SEP.join(e.russian)) for e in entries],
        )
    return {"entries": len(entries)}


def russian(conn: sqlite3.Connection, lemma: str) -> tuple[str, ...]:
    """The Russian for one lemma, or `()`. A missing table is `()` too."""
    try:
        row = conn.execute(
            "SELECT russian FROM evs_gloss WHERE lemma = ?", (lemma,)).fetchone()
    except sqlite3.Error:
        return ()
    return tuple(r for r in row[0].split(SEP) if r) if row else ()


def russian_many(conn: sqlite3.Connection, lemmas: list[str]) -> dict[str, list[str]]:
    """`russian()` for several lemmas in one query; absent lemmas are omitted."""
    wanted = sorted({l for l in lemmas if l})
    if not wanted:
        return {}
    try:
        rows = conn.execute(
            f"SELECT lemma, russian FROM evs_gloss WHERE lemma IN "
            f"({','.join('?' * len(wanted))})", wanted).fetchall()
    except sqlite3.Error:
        return {}
    return {r[0]: [w for w in r[1].split(SEP) if w] for r in rows}


def imported(conn: sqlite3.Connection) -> int:
    try:
        return conn.execute("SELECT COUNT(*) FROM evs_gloss").fetchone()[0]
    except sqlite3.Error:
        return 0
