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
    from . import config, psv

    path = Path(path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # EKI's learner dictionary lives here too, and whichever module opens the
    # file first has to leave it complete -- otherwise `psv.imported()` reads
    # "no table" on a deployment that simply has not imported the file yet, and
    # absent and zero say different things (`eesti/vocab.py` has the same note
    # for the same reason).
    conn.executescript(psv.SCHEMA)
    _migrate(conn)
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
    # `words` was just replaced wholesale, which wipes `level_source` and every
    # level EKI supplied. Re-applying here is what makes the import survive a
    # rebuild: the authoritative levels live in their own table, so this needs
    # no file and no second trip to EKI's download form.
    apply_official_levels(conn)
    return len(rows)


#: EKI's part-of-speech codes, mapped onto the vocabulary the enriched list
#: already uses — so `declines()` and every `pos LIKE '%,s,%'` query keep
#: working on a word EKI supplied and the enriched list did not.
#:
#: `G` is the genitive-attribute class (`araabia keel`), which this project
#: already calls `adjg`; `Y` is an abbreviation (`CD`, `SMS`), deliberately
#: mapped to a tag outside `DECLINABLE` so nothing tries to synthesise a
#: paradigm for an acronym. That is the rule `declines()` already applies to
#: untagged words, kept rather than quietly reversed.
EKI_POS = {
    "S": "s", "A": "adj", "V": "v", "D": "adv", "J": "conj",
    "P": "pron", "K": "postp", "N": "num", "O": "num",
    "G": "adjg", "I": "interj", "Y": "lyh",
}

#: What an EKI code this table does not know becomes.
#:
#: Not `None`, and the difference is not cosmetic. `nouns_at_level` matches on
#: `COALESCE(pos, 's')`, so a NULL part of speech is read as **noun** — and an
#: inserted word with a NULL `pos` would go straight into object-case drills
#: and have a genitive and partitive synthesised for it. That is the exact
#: failure `declines()` exists to stop, arrived at from the other side: there
#: an absent tag means "not declinable", here it would have meant "noun".
#:
#: The twelve codes above are every code the 2018 file actually uses, checked.
#: This is for the thirteenth, on the day EKI publishes one.
UNKNOWN_POS = "muu"

#: The columns EKI's file actually has: `LEMMA POS SAGEDUS TASE`, tab separated.
_EKI_COLUMNS = ("LEMMA", "POS", "SAGEDUS", "TASE")


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns an older word database does not have.

    Same reasoning as `sources._migrate`: a learner can be carrying a database
    built before a column existed, and failing to open it would lose the word
    list over one `ALTER TABLE`.
    """
    have = {r[1] for r in conn.execute("PRAGMA table_info(words)")}
    if "level_source" not in have:
        conn.execute("ALTER TABLE words ADD COLUMN level_source TEXT")


def read_official_levels(path: Path | str) -> list[tuple[str, str, str | None, int | None]]:
    """Parse EKI's level vocabulary file. Rows only — no database.

    Separated from the import so the format can be tested without one, and so a
    malformed file fails while saying what it expected rather than half-filling
    a table.
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

    Derived, not hand-maintained: `build()` calls this after replacing `words`,
    so a rebuild does not quietly drop the authoritative levels and send the
    learner back to the download form.

    Where the two disagree, EKI wins. That is not a close call — the enriched
    list's CEFR tag is a derived estimate covering 6.2 % of its lemmas, and
    this is the Estonian Language Institute publishing the levels outright.

    A word EKI knows and the enriched list does not is **inserted**, with its
    `freq_rank` left NULL. NULL is the honest value: EKI publishes a corpus
    count and this column holds a rank, and the queries that order by it
    already sort NULL last. A word with no rank drilling after one with a rank
    is right; a word ranked five million drilling first would not be.
    """
    stats = {"levelled": 0, "changed": 0, "added": 0, "unclaimed": 0,
             # Multi-word entries seen and deliberately not made drillable.
             "phrases": 0}
    rows = conn.execute("SELECT word, level, pos FROM official_levels").fetchall()
    stats["levelled"] = len(rows)
    if not rows:
        return stats

    # Drop EKI's name from any word this import no longer claims.
    #
    # `import_official_levels` replaces `official_levels` wholesale, so a
    # corrected file with a word removed used to leave that word's old level in
    # place still stamped `level_source = 'eki'` — an attribution to an
    # authority that had withdrawn it, on a function whose docstring says
    # idempotent.
    #
    # Only the attribution is cleared, because only the attribution can be. The
    # level underneath was overwritten and the enriched list's original is not
    # recoverable from here; `cli build` re-reads the TSV and then re-applies
    # this, which is the one path that restores it. The count is reported so a
    # re-import that quietly unclaims a thousand words says so.
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
                # A phrase is vocabulary; it is not a word the drill machinery
                # can act on. EKI's list carries `aru saama`, `alla kirjutama`,
                # `alles hoidma` — real and worth knowing, and inserting them
                # here would put them in `verbs_at_level`, where the
                # conjugation drill would hand `aru saama` to Vabamorf and ask
                # for its imperfect. They stay in `official_levels`, the
                # faithful record of what EKI published, and out of `words`,
                # the list of things this app generates exercises from.
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

    The file is not fetched from here, and that is deliberate. EKI serve it
    behind ID-card authentication (checked 2026-09-12) — a gate to walk through
    rather than step around. So the learner downloads `A1A2B1.txt` themselves
    and names it here.

    Licence: CC BY 4.0. EKI's own terms say the material may be processed and
    presented in any way needed, an app included, provided the attribution to
    EKI is kept and changes are described. Both are in `sources.REGISTRY`.
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
