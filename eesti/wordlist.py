"""Offline vocabulary layer built from the enriched Ekilex word list.

Source: github.com/KristjanPikhof/Estonian-Wordlist-Enriched-Ekilex
(CC-BY-SA-4.0), derived from Ekilex, so Sõnaveeb is never scraped.

Only the two small TSVs are indexed. The inflected-forms file is not used: its
de-duplicated form lists cannot be mapped back to cases. Forms come from
Vabamorf synthesis instead (`eesti.morph.case_forms`).
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
    freq_rank   INTEGER,      -- a RANK: 2 is the second commonest word
    proficiency TEXT,
    pos         TEXT,
    -- Who says so. NULL means the enriched Ekilex list, which is a derived
    -- estimate; 'eki' means the Estonian Language Institute's published level
    -- vocabulary, which is the exam board's own institute saying it outright.
    level_source TEXT
);
CREATE INDEX IF NOT EXISTS idx_words_prof ON words(proficiency);
CREATE INDEX IF NOT EXISTS idx_words_pos  ON words(pos);

-- EKI's own level vocabulary, stored verbatim and never mixed into `words`.
--
-- `Eesti keele tasemete sõnavara` (2018), CC BY 4.0, from the institute that
-- writes the exam's word lists. It is kept as its own table for two reasons.
--
-- The first is provenance: `words.proficiency` now carries claims from two
-- authorities, and `words.level_source` says which, so "who decided this word
-- is B1" is answerable rather than assumed.
--
-- The second is the trap. EKI's `freq` is a raw corpus **count** -- `aasta` is
-- 5 006 831 -- and `words.freq_rank` is a **rank**, where `ma` is 2. They are
-- the same word ordered in opposite directions, and writing one into the other
-- would have put the commonest words last in every drill that orders by
-- frequency. Two scales, one column: the bug this project already paid for
-- once with `level` and `band`. So the count stays here, under its own name.
CREATE TABLE IF NOT EXISTS official_levels (
    word  TEXT PRIMARY KEY,
    level TEXT NOT NULL,      -- A1 | A2 | B1, as EKI published it
    pos   TEXT,               -- EKI's own one-letter code, unmapped
    freq  INTEGER             -- corpus COUNT, not a rank
);
CREATE INDEX IF NOT EXISTS idx_official_level ON official_levels(level);

-- Cached Vabamorf synthesis. Populated lazily; 'distinct' records whether the
-- genitive/partitive contrast is actually testable for this word.
CREATE TABLE IF NOT EXISTS object_cases (
    word      TEXT PRIMARY KEY,
    genitive  TEXT NOT NULL,
    partitive TEXT NOT NULL,
    distinct_ INTEGER NOT NULL
);
"""


#: Parts of speech that take case endings. `adjg` (genitive-only adjectives such
#: as `eri`) has no paradigm.
DECLINABLE = frozenset({"s", "adj", "num", "pron", "prop"})


def declines(pos: str | None) -> bool:
    """Can this word take a case ending at all?

    Vabamorf synthesises a "genitive" for anything (`alguses` → `algusese`), so
    the part of speech must be checked first. Untagged words count as not
    declinable: they are mostly acronyms, genitive forms filed as headwords and
    imperatives.
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
    # Resolved at call time, so configuration and tests can redirect it.
    from . import config, psv

    path = Path(path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # Apply the EKI tables' schemas too, so `psv.imported()` reads zero rather than
    # "no table" before an import.
    conn.executescript(psv.SCHEMA)
    _migrate(conn)
    return conn


def available(path: Path | None = None) -> bool:
    """True when there is a word list here with words actually in it.

    `connect` creates the file and schema, so an empty path looks like a database;
    ask this before trusting a fresh path.
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

    Also drops `object_cases`, the derived cache, so removed or re-tagged words
    are recomputed rather than served stale.
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
    # `words` was just replaced, so re-apply EKI's levels from their own table.
    apply_official_levels(conn)
    return len(rows)


#: EKI's part-of-speech codes mapped onto the enriched list's vocabulary, so
#: `declines()` and `pos` queries work for EKI-only words. `Y` (abbreviation) maps
#: outside `DECLINABLE`.
EKI_POS = {
    "S": "s", "A": "adj", "V": "v", "D": "adv", "J": "conj",
    "P": "pron", "K": "postp", "N": "num", "O": "num",
    "G": "adjg", "I": "interj", "Y": "lyh",
}

#: Tag for an unknown EKI code. Not `None`: `nouns_at_level` reads a NULL `pos`
#: as a noun, which would put an unknown word into object-case drills.
UNKNOWN_POS = "muu"

#: The columns EKI's file actually has: `LEMMA POS SAGEDUS TASE`, tab separated.
_EKI_COLUMNS = ("LEMMA", "POS", "SAGEDUS", "TASE")


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns an older word database does not have, so it still opens."""
    have = {r[1] for r in conn.execute("PRAGMA table_info(words)")}
    if "level_source" not in have:
        conn.execute("ALTER TABLE words ADD COLUMN level_source TEXT")


def read_official_levels(path: Path | str) -> list[tuple[str, str, str | None, int | None]]:
    """Parse EKI's level vocabulary file into rows, without a database, failing with
    a clear message on a malformed file.
    """
    path = Path(path)
    rows: list[tuple[str, str, str | None, int | None]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = set(_EKI_COLUMNS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"{path} does not look like EKI's level vocabulary: "
                f"missing column(s) {sorted(missing)}. Expected a tab-separated "
                f"file whose header is {' '.join(_EKI_COLUMNS)}."
            )
        for rec in reader:
            word = (rec.get("LEMMA") or "").strip()
            level = (rec.get("TASE") or "").strip().upper()
            if not word or level not in LEVELS:
                continue
            freq = (rec.get("SAGEDUS") or "").strip()
            rows.append((
                word,
                level,
                (rec.get("POS") or "").strip().upper() or None,
                int(freq) if freq.isdigit() else None,
            ))
    return rows


def apply_official_levels(conn: sqlite3.Connection) -> dict[str, int]:
    """Let EKI's levels win in `words`, and say so in `level_source`.

    Called by `build()` after `words` is replaced. EKI's published level beats the
    enriched list's estimate. Words EKI knows and the list does not are inserted
    with `freq_rank` NULL (EKI gives a corpus count, not a rank), which sorts last.
    """
    stats = {"levelled": 0, "changed": 0, "added": 0, "unclaimed": 0,
             # Multi-word entries seen and deliberately not made drillable.
             "phrases": 0}
    rows = conn.execute("SELECT word, level, pos FROM official_levels").fetchall()
    stats["levelled"] = len(rows)
    if not rows:
        return stats

    # Clear `level_source = 'eki'` from words this import no longer lists. Only the
    # attribution can be cleared; `cli build` restores the original levels. The count
    # is reported.
    with conn:
        stats["unclaimed"] = conn.execute(
            "UPDATE words SET level_source = NULL"
            " WHERE level_source = 'eki'"
            "   AND word NOT IN (SELECT word FROM official_levels)"
        ).rowcount

    with conn:
        for row in rows:
            word, level, eki_pos = row["word"], row["level"], row["pos"]
            current = conn.execute(
                "SELECT proficiency FROM words WHERE word = ?", (word,)
            ).fetchone()
            if current is None:
                # Multi-word phrases (`aru saama`) stay in `official_levels` only: `words` is
                # what generators act on, and a phrase cannot be conjugated.
                if " " in word:
                    stats["phrases"] += 1
                    continue
                conn.execute(
                    "INSERT INTO words(word, freq_rank, proficiency, pos, level_source)"
                    " VALUES (?, NULL, ?, ?, 'eki')",
                    (word, level, EKI_POS.get(eki_pos or "", UNKNOWN_POS)),
                )
                stats["added"] += 1
                continue
            if current["proficiency"] != level:
                stats["changed"] += 1
            conn.execute(
                "UPDATE words SET proficiency = ?, level_source = 'eki' WHERE word = ?",
                (level, word),
            )
    return stats


def import_official_levels(
    conn: sqlite3.Connection, path: Path | str
) -> dict[str, int]:
    """Load EKI's level vocabulary and apply it. Idempotent.

    Reads a local file (committed as `deploy/eki/A1A2B1.txt`); nothing fetches from
    EKI. CC BY 4.0 with attribution in `licences.REGISTRY`.
    """
    rows = read_official_levels(path)
    with conn:
        conn.execute("DELETE FROM official_levels")
        conn.executemany(
            "INSERT OR REPLACE INTO official_levels(word, level, pos, freq)"
            " VALUES (?,?,?,?)",
            rows,
        )
    stats = apply_official_levels(conn)
    for level in LEVELS:
        stats[level] = sum(1 for r in rows if r[1] == level)
    return stats


def nouns_at_level(
    conn: sqlite3.Connection, levels: tuple[str, ...] = LEVELS, limit: int = 5000
) -> list[Word]:
    """Nouns tagged at the given CEFR levels, most frequent first (rank 0 means no
    data and sorts last).
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
    """Verbs tagged at the given CEFR levels, most frequent first. Shared by
    `conjugation.py` and `verbs.py` so both agree on the verb pool.
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
    """Synthesise genitive/partitive for level-appropriate nouns and cache them.

    `distinct_` filters out words whose two forms are identical, which cannot be
    drilled.
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


def object_case_rows(conn: sqlite3.Connection, words: list[str]) -> list[sqlite3.Row]:
    """Case forms for specific words, synthesising and caching any not yet indexed
    (curated pools include words without a CEFR tag).
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
