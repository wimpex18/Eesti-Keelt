"""Offline vocabulary layer built from the enriched Ekilex word list.

Source: github.com/KristjanPikhof/Estonian-Wordlist-Enriched-Ekilex (CC-BY-SA-4.0,
snapshot 2026-04-01), derived from Ekilex — the same database behind Sonaveeb and
the Sonastik app. Using it means we never scrape Sonaveeb, whose maintainers
explicitly ask people not to batch-request it.

Only the two small TSVs are indexed. The 79 MB inflected-forms file is
deliberately NOT used: its per-word form lists are de-duplicated, so identical
forms collapse and position can no longer be mapped to a case ("auto" has 13
singular entries, not 14). Vabamorf synthesis gives labelled, trustworthy forms
instead — see eesti.morph.case_forms.
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import DB_PATH, LEVELS, RAW

SCHEMA = """
CREATE TABLE IF NOT EXISTS words (
    word        TEXT PRIMARY KEY,
    freq_rank   INTEGER,
    proficiency TEXT,
    pos         TEXT
);
CREATE INDEX IF NOT EXISTS idx_words_prof ON words(proficiency);
CREATE INDEX IF NOT EXISTS idx_words_pos  ON words(pos);

-- Cached Vabamorf synthesis. Populated lazily; 'distinct' records whether the
-- genitive/partitive contrast is actually testable for this word.
CREATE TABLE IF NOT EXISTS object_cases (
    word      TEXT PRIMARY KEY,
    genitive  TEXT NOT NULL,
    partitive TEXT NOT NULL,
    distinct_ INTEGER NOT NULL
);
"""


@dataclass(frozen=True)
class Word:
    word: str
    freq_rank: int | None
    proficiency: str | None
    pos: str | None


def connect(path: Path | None = None) -> sqlite3.Connection:
    # Resolved at call time, not import time. Where the database lives is
    # configuration, and configuration frozen into a module constant at import
    # cannot be redirected — which is how a whole class of tests ended up
    # silently depending on the developer's own build.
    from . import config

    path = Path(path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def build(conn: sqlite3.Connection, raw_dir: Path | None = None) -> int:
    """Import the word list TSV. Idempotent — safe to re-run after a refresh."""
    raw_dir = Path(raw_dir or RAW)
    src = raw_dir / "est_words_160k.tsv"
    if not src.exists():
        raise FileNotFoundError(
            f"{src} missing — run `python -m eesti.cli fetch-data` first."
        )

    rows = []
    with src.open(encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            word = (rec.get("word") or "").strip()
            if not word:
                continue
            raw_rank = (rec.get("freq_rank") or "").strip()
            rows.append(
                (
                    word,
                    int(raw_rank) if raw_rank.isdigit() else None,
                    (rec.get("proficiency") or "").strip() or None,
                    (rec.get("pos") or "").strip() or None,
                )
            )

    with conn:
        conn.execute("DELETE FROM words")
        conn.executemany(
            "INSERT OR REPLACE INTO words(word, freq_rank, proficiency, pos) "
            "VALUES (?,?,?,?)",
            rows,
        )
    return len(rows)


def nouns_at_level(
    conn: sqlite3.Connection, levels: tuple[str, ...] = LEVELS, limit: int = 5000
) -> list[Word]:
    """Nouns tagged at the given CEFR levels, most frequent first.

    Frequency ordering matters pedagogically: drilling `raamat` before some rare
    B1 noun is a better use of a study session. A freq_rank of 0 in the source
    means "no frequency data", so it sorts with NULL rather than first.
    """
    marks = ",".join("?" * len(levels))
    cur = conn.execute(
        f"""SELECT word, freq_rank, proficiency, pos FROM words
            WHERE proficiency IN ({marks})
              AND (','||COALESCE(pos,'s')||',') LIKE '%,s,%'
            ORDER BY (freq_rank IS NULL OR freq_rank = 0), freq_rank
            LIMIT ?""",
        (*levels, limit),
    )
    return [Word(**dict(r)) for r in cur]


def index_object_cases(
    conn: sqlite3.Connection, levels: tuple[str, ...] = LEVELS, limit: int = 5000
) -> dict[str, int]:
    """Synthesize genitive/partitive for level-appropriate nouns and cache them.

    Runs Vabamorf, so it is slow-ish once and instant thereafter. The `distinct_`
    flag is the drill generator's filter: words whose two forms are identical
    ("maja"/"maja") cannot be got wrong and make worthless drills.
    """
    from .morph import case_forms  # local import: keeps morph optional for tests

    known = {r["word"] for r in conn.execute("SELECT word FROM object_cases")}
    stats = {"checked": 0, "indexed": 0, "distinct": 0, "unknown": 0}
    batch = []
    for w in nouns_at_level(conn, levels, limit):
        if w.word in known:
            continue
        stats["checked"] += 1
        forms = case_forms(w.word)
        if not forms:
            stats["unknown"] += 1
            continue
        is_distinct = int(forms["genitive"] != forms["partitive"])
        stats["indexed"] += 1
        stats["distinct"] += is_distinct
        batch.append((w.word, forms["genitive"], forms["partitive"], is_distinct))

    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO object_cases(word, genitive, partitive, distinct_)"
            " VALUES (?,?,?,?)",
            batch,
        )
    return stats


def drillable_nouns(
    conn: sqlite3.Connection, levels: tuple[str, ...] = LEVELS, limit: int = 200
) -> list[sqlite3.Row]:
    """Level-appropriate nouns with a genuinely distinct genitive vs partitive."""
    marks = ",".join("?" * len(levels))
    return list(
        conn.execute(
            f"""SELECT o.word, o.genitive, o.partitive, w.proficiency, w.freq_rank
                FROM object_cases o JOIN words w ON w.word = o.word
                WHERE o.distinct_ = 1 AND w.proficiency IN ({marks})
                ORDER BY (w.freq_rank IS NULL OR w.freq_rank = 0), w.freq_rank
                LIMIT ?""",
            (*levels, limit),
        )
    )


def object_case_rows(conn: sqlite3.Connection, words: list[str]) -> list[sqlite3.Row]:
    """Case forms for specific words, synthesizing and caching any not yet indexed.

    The drill pools are curated by meaning, so they contain words that the CEFR
    index may not cover (compounds like "kodutöö" often carry no proficiency tag).
    Rather than dropping them we synthesize on demand — the forms are what matter,
    the CEFR tag is only used for display.
    """
    from .morph import case_forms

    if not words:
        return []
    known = {
        r["word"] for r in conn.execute(
            f"SELECT word FROM object_cases WHERE word IN ({','.join('?' * len(words))})",
            words,
        )
    }
    missing = [w for w in words if w not in known]
    if missing:
        batch = []
        for w in missing:
            forms = case_forms(w)
            if forms:
                batch.append(
                    (w, forms["genitive"], forms["partitive"],
                     int(forms["genitive"] != forms["partitive"]))
                )
        with conn:
            conn.executemany(
                "INSERT OR REPLACE INTO object_cases(word, genitive, partitive,"
                " distinct_) VALUES (?,?,?,?)",
                batch,
            )

    marks = ",".join("?" * len(words))
    return list(
        conn.execute(
            f"""SELECT o.word, o.genitive, o.partitive, o.distinct_, w.proficiency
                FROM object_cases o LEFT JOIN words w ON w.word = o.word
                WHERE o.word IN ({marks})""",
            words,
        )
    )
