"""Estonian definitions from EKI's native-level dictionaries: VSL, and EKSS if imported.

Two downloads from arhiiv.eki.ee/litsents share one shape (measured 2026-09-13):
a headword `m`, and definitions `d` under the article's `S`.

* **vsl** — *Võõrsõnade leksikon*: 31 794 articles on loanwords (`idee`,
  `aktiivne`), definitions written for a native reader.
* **ekss** — *Eesti keele seletav sõnaraamat*: 145 882 articles, 117 937
  lemmas with a definition — 96 058 of them in the word list. Committed and
  imported by the build (measured 2026-09-13).

Both are the **last** Estonian definition a word card falls back to: EKI's
learner-level PSV first, Sõnaveeb second, these third — so they fill a gap only
when Sõnaveeb has nothing to say or cannot be asked (offline, over budget,
down). Native-level wording is the thing PSV exists to replace, so it never
goes ahead of either. The order is stated once, in `api/grammar._meaning`.

Kept per lemma: the first definition of the first article. Sub-articles (`AA`,
VSL's phrase entries like *aktiivne kaubabilanss*) are not headwords a learner
clicks and are skipped. Each dictionary has its own table and neither writes the
other's, or `psv_gloss`, or the learner's `word_gloss`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import ekixml

#: Source id -> table. A new dictionary of this shape is one line here.
TABLES = {"eki-vsl": "vsl_gloss", "eki-ekss": "ekss_gloss"}


#: A sense EKI mark obsolete — 248 in VSL (measured 2026-09-13) — is skipped
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
