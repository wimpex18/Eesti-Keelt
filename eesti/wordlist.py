"""Offline vocabulary layer built from the enriched Ekilex word list.

Source: github.com/KristjanPikhof/Estonian-Wordlist-Enriched-Ekilex (CC-BY-SA-4.0,
snapshot 2026-04-01), derived from Ekilex — the same database behind Sõnaveeb and
the Sõnastik app. Using it means we never scrape Sõnaveeb, whose maintainers
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

from .config import LEVELS

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


#: Parts of speech that actually take case endings in Estonian.
#:
#: Nouns, adjectives, numerals, pronouns and proper nouns decline; adverbs,
#: interjections, adpositions and conjunctions do not. `adjg` is the
#: genitive-only adjective class (`eri`, `puht`), which by definition has no
#: paradigm to build.
DECLINABLE = frozenset({"s", "adj", "num", "pron", "prop"})


def declines(pos: str | None) -> bool:
    """Can this word take a case ending at all?

    Vabamorf will synthesise a genitive for anything you hand it, including
    words that have none. Ask it for the genitive of `alguses` -- an adverb,
    itself the inessive of `algus` -- and it returns `algusese`, which is not
    an Estonian word. The synthesiser is not wrong; it is being asked the wrong
    question, and the only thing that can stop that is knowing the part of
    speech first.

    An untagged word counts as **not** declinable, which inverts the rule used
    for CEFR levels elsewhere in this project, and deliberately. There, an
    absent tag meant "nobody rated this" and dropping it would have lost real
    words. Here an absent tag correlates with the entry not being a lemma at
    all -- the untagged set is acronyms (`dna`, `nato`, `who`), genitive forms
    filed as headwords (`kahe`, `linna`, `panga`) and verb imperatives (`küsi`,
    `õpi`) -- and the cost of keeping them is printing a non-word to a learner
    in the same citation format as `raamat, raamatu, raamatut`.
    """
    if not pos:
        return False
    return bool({p.strip() for p in pos.split(",")} & DECLINABLE)


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


def available(path: Path | None = None) -> bool:
    """True when there is a word list here with words actually in it.

    `connect` creates: `sqlite3.connect` makes the file, and the schema follows,
    so opening a path that holds nothing hands back a complete-looking database
    with zero rows. That is this project's oldest recurring bug -- twice already
    it made an empty deployment look full -- and the rule written down for it is
    "presence of a database is not presence of data. Count rows."

    `connect` keeps creating, because `cli build` has to be able to make the
    file. So the answer is a separate question rather than a refusal: ask this
    before trusting what a fresh path contains.
    """
    from . import config

    target = Path(path or config.DB_PATH)
    if not target.exists():
        return False
    try:
        with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as conn:
            return conn.execute("SELECT 1 FROM words LIMIT 1").fetchone() is not None
    except sqlite3.Error:
        # No file, no table, or not a database at all -- all the same answer.
        return False


def build(conn: sqlite3.Connection, raw_dir: Path | None = None) -> int:
    """Import the word list TSV. Idempotent — safe to re-run after a refresh.

    "Idempotent" used to be true of `words` and false of everything derived
    from it. This replaced the word list and left `object_cases` untouched, and
    `index_object_cases` skips any word it already has — so a refresh could
    neither drop a cached paradigm for a word upstream had removed, nor
    recompute one whose part of speech had been corrected. The cache was
    write-once for the life of the database.

    So the derived table goes too. Rebuilding it costs 2.4 s over 2 575 words,
    which is not worth a stale answer about what a word means.
    """
    from . import config

    raw_dir = Path(raw_dir or config.RAW)
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
        # Derived from the rows above, so it cannot outlive them.
        conn.execute("DELETE FROM object_cases")
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


def verbs_at_level(
    conn: sqlite3.Connection, levels: tuple[str, ...] = LEVELS, limit: int = 400
) -> list[tuple[str, str]]:
    """Verbs tagged at the given CEFR levels, most frequent first.

    The twin of `nouns_at_level`, and here for the reason that one is here:
    this query was written out twice, identically, in `conjugation.py` and
    `verbs.py` -- two modules that must agree about which verbs a learner is
    ready for, with nothing to keep them in step. One of them changing the
    `pos` test or the frequency ordering would have changed which verbs the
    drill offered and not which verbs the form model considered irregular.

    Frequency order matters more for verbs than for nouns: a learner meets
    *saama* and *tegema* every day and *sarnanema* almost never, so drilling
    the conditional is worth far more on the first than the second.
    """
    marks = ",".join("?" * len(levels))
    return [
        (row[0], row[1])
        for row in conn.execute(
            f"""SELECT word, proficiency FROM words
                WHERE proficiency IN ({marks})
                  AND (','||COALESCE(pos,'')||',') LIKE '%,v,%'
                ORDER BY (freq_rank IS NULL OR freq_rank = 0), freq_rank
                LIMIT ?""",
            (*levels, limit),
        )
    ]


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
