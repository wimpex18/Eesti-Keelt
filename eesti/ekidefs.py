"""Estonian definitions from EKI's native-level dictionaries: VSL and EKSS.

Both share one shape — a headword `m` and definitions `d` under `S`:

* **vsl** — *Võõrsõnade leksikon*: loanwords, native-level definitions;
* **ekss** — *Eesti keele seletav sõnaraamat*: the explanatory dictionary.

They are the last definition fallback (PSV, then the live dictionary, then
these), ordered in `api/grammar._meaning`. Kept per lemma: the first current
definition of the first article; sub-articles (`AA`, phrase entries) are
skipped. Each dictionary has its own table.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import ekixml

#: Source id -> table. A new dictionary of this shape is one line here.
TABLES = {"eki-vsl": "vsl_gloss", "eki-ekss": "ekss_gloss"}


#: A sense EKI mark obsolete — 248 in VSL — is skipped
#: when a current one exists; the first definition is not always the one a
#: learner meets.
ARCHAIC = "van"


def _first_current(article) -> str:
    fallback = ""
    for dg in article.find("S").iter("dg") if article.find("S") is not None else ():
        text = ekixml.text(dg.find("d"))
        if not text:
            continue
        if ARCHAIC not in {ekixml.text(s) for s in dg.findall("s")}:
            return text
        fallback = fallback or text
    return fallback


def parse(path: Path | str) -> dict[str, str]:
    """lemma -> first definition, first article per lemma winning."""
    found: dict[str, str] = {}
    for article in ekixml.articles(path):
        lemmas = [l for l in ekixml.headwords(article) if l not in found]
        if not lemmas:
            continue
        definition = _first_current(article)
        for lemma in lemmas if definition else ():
            found[lemma] = definition
    return found


def _schema(table: str) -> str:
    return (f"CREATE TABLE IF NOT EXISTS {table} "
            f"(lemma TEXT PRIMARY KEY, definition TEXT NOT NULL)")


def store(conn: sqlite3.Connection, source: str, definitions: dict[str, str]) -> int:
    table = TABLES[source]
    conn.execute(_schema(table))
    with conn:
        conn.execute(f"DELETE FROM {table}")
        conn.executemany(f"INSERT INTO {table} (lemma, definition) VALUES (?,?)",
                         definitions.items())
    return len(definitions)


def lookup(conn: sqlite3.Connection, lemma: str) -> tuple[str, str] | None:
    """(source id, definition) from the first dictionary that has the lemma."""
    for source, table in TABLES.items():
        try:
            row = conn.execute(
                f"SELECT definition FROM {table} WHERE lemma = ?", (lemma,)).fetchone()
        except sqlite3.Error:
            continue
        if row:
            return source, row[0]
    return None


def imported(conn: sqlite3.Connection, source: str) -> int:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {TABLES[source]}").fetchone()[0]
    except sqlite3.Error:
        return 0
