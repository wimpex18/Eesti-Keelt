"""Word lookup against the exported form index (`edge.db`).

Click any word for its lemma, its case and whether it is at the learner's level.
Needs no Vabamorf at runtime.
"""

from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path

from .config import DATA

EDGE_DB = DATA / "edge.db"

# Human-readable Estonian names for the tags the export stores, so the reader
# teaches the grammar vocabulary the exam uses rather than terse codes. The tags and
# what each denotes are Vabamorf's own categories (filosoft.ee, "Morfoloogilise
# analüüsi väljund"); every tag in `forms` has a name, so no code reaches the card.
_CASES = {
    "n": "nimetav", "g": "omastav", "p": "osastav", "ill": "sisseütlev",
    "in": "seesütlev", "el": "seestütlev", "all": "alaleütlev", "ad": "alalütlev",
    "abl": "alaltütlev", "tr": "saav", "ter": "rajav", "es": "olev",
    "ab": "ilmaütlev", "kom": "kaasaütlev",
}
# The Russian gloss for each case, as the drills explain it (`cloze.CASES`, which
# `tests/test_lookup_tags.py` holds this table to). Nominative is not drilled there.
_CASES_RU = {
    "n": "именительный", "g": "родительный", "p": "частичный",
    "ill": "иллатив (куда)", "in": "инессив (где, внутри)",
    "el": "элатив (откуда, изнутри)", "all": "аллатив (кому, на что)",
    "ad": "адессив (у кого, на чём)", "abl": "аблатив (от кого, с чего)",
    "tr": "транслатив (кем/чем становится)", "ter": "терминатив (до)",
    "es": "эссив (в качестве)", "ab": "абессив (без)",
    "kom": "комитатив (с кем/чем)",
}
TAG_NAMES = {
    **{f"sg {c}": f"ainsuse {name}" for c, name in _CASES.items()},
    **{f"pl {c}": f"mitmuse {name}" for c, name in _CASES.items()},
    "n": "olevik, mina", "d": "olevik, sina", "b": "olevik, tema",
    "me": "olevik, meie", "te": "olevik, teie", "vad": "olevik, nemad",
    "sin": "minevik, mina", "s": "minevik, tema", "sime": "minevik, meie",
    "site": "minevik, teie", "sid": "minevik, sina / nemad",
    "takse": "umbisikuline olevik", "ti": "umbisikuline minevik",
    "nud": "mineviku kesksõna", "tud": "umbisikuline kesksõna",
    "ge": "käskiv kõneviis, teie", "gu": "käskiv kõneviis, tema / nemad",
    "da": "da-infinitiiv", "ma": "ma-infinitiiv", "ks": "tingiv kõneviis",
}
TAG_RU = {
    **{f"sg {c}": f"ед. ч., {ru}" for c, ru in _CASES_RU.items()},
    **{f"pl {c}": f"мн. ч., {ru}" for c, ru in _CASES_RU.items()},
    "n": "наст. вр., я", "d": "наст. вр., ты", "b": "наст. вр., он/она",
    "me": "наст. вр., мы", "te": "наст. вр., вы", "vad": "наст. вр., они",
    "sin": "прош. вр., я", "s": "прош. вр., он/она", "sime": "прош. вр., мы",
    "site": "прош. вр., вы", "sid": "прош. вр., ты / они",
    "takse": "безличная форма, наст. вр.", "ti": "безличная форма, прош. вр.",
    "nud": "причастие прошедшего времени", "tud": "безличное причастие",
    "ge": "повелительное, вы", "gu": "повелительное, пусть он/они",
    "da": "инфинитив на -da", "ma": "инфинитив на -ma", "ks": "условное наклонение",
}


WORD_RE = re.compile(r"[A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü]+", re.UNICODE)


@lru_cache(maxsize=1)
def _open(target: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _db(path: str | None = None) -> sqlite3.Connection | None:
    """The forms database, opened once — but its absence is never cached, so a file
    created after start-up (`cli export`) is picked up without a restart.
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
            "tags": [{"tag": t, "name": TAG_NAMES.get(t, t), "ru": TAG_RU.get(t, "")}
                     for t in tags],
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
    """Distinct lemmas a passage uses, for coverage (a known lemma is known in every
    inflection).
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
    """Vocabulary profile of a passage: which words are at or above your level."""
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
    """A word in its dictionary citation form.

    Estonian nouns are cited by three **põhivormid** — nominative, genitive,
    partitive (`raamat, raamatu, raamatut`) — since every other case builds on the
    genitive stem. Generated by Vabamorf on demand, so no word store is needed.
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
