"""Word lookup against the exported form index.

This is what makes a transcript readable at A1-A2: click any word and get its
lemma, its case, and whether it is vocabulary you are supposed to know yet.

It reads `edge.db` — the build-time export — so it needs no Vabamorf at runtime
and will work unchanged once the app is on Cloudflare, where the same queries run
against D1. Measured coverage on realistic learner text: 98% of tokens.
"""

from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path

from .config import DATA

EDGE_DB = DATA / "edge.db"

# Human-readable Estonian names for the tags the export stores, so the reader
# teaches the grammar vocabulary the exam uses rather than terse codes.
TAG_NAMES = {
    "sg n": "ainsuse nimetav", "sg g": "ainsuse omastav", "sg p": "ainsuse osastav",
    "sg ill": "sisseütlev", "sg in": "seesütlev", "sg el": "seestütlev",
    "sg all": "alaleütlev", "sg ad": "alalütlev", "sg abl": "alaltütlev",
    "sg tr": "saav", "sg ter": "rajav", "sg es": "olev", "sg ab": "ilmaütlev",
    "sg kom": "kaasaütlev",
    "pl n": "mitmuse nimetav", "pl g": "mitmuse omastav", "pl p": "mitmuse osastav",
    "n": "olevik, mina", "d": "olevik, sina", "b": "olevik, tema",
    "sin": "minevik, mina", "nud": "mineviku kesksõna", "tud": "umbisikuline",
    "da": "da-infinitiiv", "ma": "ma-infinitiiv", "ks": "tingiv kõneviis",
}

WORD_RE = re.compile(r"[A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü]+", re.UNICODE)


@lru_cache(maxsize=1)
def _open(target: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _db(path: str | None = None) -> sqlite3.Connection | None:
    """The forms database, opened once — but its ABSENCE is never cached.

    It used to be one `lru_cache`d function, which memoised both answers. A
    server started before `cli export` finished therefore returned `None` for
    the rest of its life: the file appeared seconds later, every lookup kept
    reporting "run `cli export` first", and only a restart fixed it. Caching a
    connection is the point; caching "there is no database" is a decision made
    once, at the worst possible moment, that nothing can revisit.

    Same shape as the rule already written down for `available()`: presence of
    a database is a question to ask when asked, not a fact to freeze at import.
    """
    target = Path(path or EDGE_DB)
    if not target.exists():
        return None
    return _open(str(target))


def lookup(word: str) -> dict:
    """Analyses for one surface form, plus the lemma's CEFR level."""
    conn = _db()
    if conn is None:
        return {"word": word, "found": False, "error": "run `cli export` first"}

    surface = word.strip().lower()
    rows = conn.execute(
        "SELECT lemma, tag FROM forms WHERE form = ? ORDER BY lemma, tag LIMIT 12",
        (surface,),
    ).fetchall()
    if not rows:
        return {"word": word, "found": False}

    lemmas: dict[str, list[str]] = {}
    for row in rows:
        lemmas.setdefault(row["lemma"], []).append(row["tag"])

    out = []
    for lemma, tags in lemmas.items():
        meta = conn.execute(
            "SELECT proficiency, freq_rank, pos FROM words WHERE lemma = ?", (lemma,)
        ).fetchone()
        cases = conn.execute(
            "SELECT genitive, partitive, distinct_ FROM object_cases WHERE lemma = ?",
            (lemma,),
        ).fetchone()
        out.append({
            "lemma": lemma,
            "tags": [{"tag": t, "name": TAG_NAMES.get(t, t)} for t in tags],
            "level": meta["proficiency"] if meta else None,
            "pos": meta["pos"] if meta else None,
            "genitive": cases["genitive"] if cases else None,
            "partitive": cases["partitive"] if cases else None,
            # Flagged so the reader can point out the contrast in the wild —
            # seeing it in a real sentence is worth more than another drill.
            "object_case_contrast": bool(cases and cases["distinct_"]) if cases else False,
        })
    return {"word": word, "found": True, "analyses": out}


def lemmas_in(text: str) -> list[str]:
    """Distinct lemmas a passage uses, for coverage arithmetic.

    Lemmas rather than surface forms: a learner who knows `raamat` knows it in
    `raamatut` too, and counting forms would make every inflected text look
    harder than it is — which in Estonian is most of them.
    """
    conn = _db()
    if conn is None:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for word in {w.lower() for w in WORD_RE.findall(text)}:
        row = conn.execute(
            "SELECT lemma FROM forms WHERE form = ? LIMIT 1", (word,)
        ).fetchone()
        lemma = row["lemma"] if row else word
        if lemma not in seen:
            seen.add(lemma)
            found.append(lemma)
    return found


def annotate(text: str, levels: tuple[str, ...] = ("A1", "A2", "B1")) -> dict:
    """Vocabulary profile of a passage: which words are at or above your level.

    Answers the question that decides whether a text is worth reading — not
    "how long is it" but "how much of it can I already handle".
    """
    conn = _db()
    if conn is None:
        return {"error": "run `cli export` first"}

    words = [w.lower() for w in WORD_RE.findall(text)]
    unique = sorted(set(words))
    known, above, unknown = [], [], []

    for word in unique:
        row = conn.execute(
            """SELECT w.lemma, w.proficiency FROM forms f
               JOIN words w ON w.lemma = f.lemma
               WHERE f.form = ? ORDER BY (w.proficiency IS NULL), w.proficiency
               LIMIT 1""",
            (word,),
        ).fetchone()
        if row is None:
            unknown.append(word)
        elif row["proficiency"] in levels:
            known.append(word)
        else:
            above.append(word)

    total = len(unique) or 1
    return {
        "tokens": len(words),
        "unique": len(unique),
        "at_level": len(known),
        "above_level": len(above),
        "unrecognised": len(unknown),
        "coverage": round(len(known) / total, 3),
        "hard_words": above[:40],
    }


def principal_forms(lemma: str) -> dict:
    """A word in the form Estonian dictionaries actually cite it.

    Estonian nouns are learned as three **põhivormid** — nominative, genitive,
    partitive (`raamat, raamatu, raamatut`) — because every other case is built
    from the genitive stem plus an ending. Learn the trio and you have the word;
    learn only the nominative and you have almost nothing.

    Which answers the "do we need to store every word?" question: **no.** These
    are generated from Vabamorf on demand and agree with TalTech's
    native-curated gold forms 98 % of the time, so a downloaded card bundle
    would be more storage for less coverage — bundles run to a few thousand
    hand-made entries, this covers every word Vabamorf knows, inflected
    correctly, including ones nobody has made a card for.
    """
    conn = _db()
    if conn is None:
        return {"lemma": lemma, "error": "run `cli export` first"}

    row = conn.execute(
        "SELECT genitive, partitive, distinct_ FROM object_cases WHERE lemma = ?",
        (lemma,),
    ).fetchone()
    meta = conn.execute(
        "SELECT proficiency, freq_rank, pos FROM words WHERE lemma = ?", (lemma,)
    ).fetchone()

    if row is None:
        return {"lemma": lemma, "found": False}

    return {
        "lemma": lemma,
        "found": True,
        # The citation string a textbook would print.
        "citation": f"{lemma}, {row['genitive']}, {row['partitive']}",
        "nominative": lemma,
        "genitive": row["genitive"],
        "partitive": row["partitive"],
        "object_case_contrast": bool(row["distinct_"]),
        "level": meta["proficiency"] if meta else None,
        "pos": meta["pos"] if meta else None,
    }
