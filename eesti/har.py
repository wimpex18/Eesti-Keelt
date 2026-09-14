"""*Haridussõnastik* — EKI's education terms, with their Russian.

Each article is a term (`aabits`, `eksam`, `hinne`) with translations. Headword
at `P/ep/terg/ter`: a preferred term (`tyyp="ee"`) plus synonyms (`tyyp="sy"`);
translations directly under `S`.

Only the Russian is used, as the last gloss fallback (order in `meaning.py`).
Every term, preferred or synonym, maps to its article's Russian in `har_gloss`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import ekixml

MAX_RUSSIAN = 3

#: `har_tyybid.xsd` `s_tyyp`: `halb` is EKI calling a term wrong, `van`
#: obsolete. 72 translations carry one.
NOT_USED = {"halb", "van"}
SEP = "\x1f"

SCHEMA = """
CREATE TABLE IF NOT EXISTS har_gloss (
    lemma   TEXT PRIMARY KEY,
    russian TEXT NOT NULL      -- \x1f-joined
);
"""


def parse(path: Path | str) -> dict[str, tuple[str, ...]]:
    """term -> Russian translations, first article per term winning."""
    found: dict[str, tuple[str, ...]] = {}
    for article in ekixml.articles(path):
        russian: list[str] = []
        for xp in article.findall("S/xp"):
            if xp.get(ekixml.XML_LANG) != "ru":
                continue
            for xg in xp.findall("xg"):
                if {ekixml.text(s) for s in xg.findall("s")} & NOT_USED:
                    continue
                word = ekixml.russian(xg.find("x"))
                if word and word not in russian:
                    russian.append(word)
        if not russian:
            continue
        # A term EKI mark `halb` or `van` is still one a learner can meet in
        # an old text, so it keeps its gloss; only the translations so marked
        # are dropped. Preferred terms first, so a synonym never claims first.
        terms = sorted(article.findall("P/ep/terg"),
                       key=lambda g: g.find("ter") is None or g.find("ter").get("tyyp") != "ee")
        for terg in terms:
            for lemma in ekixml.headwords(terg, tag="ter"):
                if lemma not in found:
                    found[lemma] = tuple(russian[:MAX_RUSSIAN])
    return found


def store(conn: sqlite3.Connection, terms: dict[str, tuple[str, ...]]) -> int:
    conn.executescript(SCHEMA)
    with conn:
        conn.execute("DELETE FROM har_gloss")
        conn.executemany("INSERT INTO har_gloss (lemma, russian) VALUES (?,?)",
                         [(k, SEP.join(v)) for k, v in terms.items()])
    return len(terms)


def russian(conn: sqlite3.Connection, lemma: str) -> tuple[str, ...]:
    try:
        row = conn.execute("SELECT russian FROM har_gloss WHERE lemma = ?",
                           (lemma,)).fetchone()
    except sqlite3.Error:
        return ()
    return tuple(r for r in row[0].split(SEP) if r) if row else ()


def imported(conn: sqlite3.Connection) -> int:
    try:
        return conn.execute("SELECT COUNT(*) FROM har_gloss").fetchone()[0]
    except sqlite3.Error:
        return 0
