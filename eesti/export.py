"""Build-time export: Vabamorf's forms as a portable lookup dataset (`edge.db`).

Generates labelled forms once, at build time, so word lookup is an indexed
SELECT instead of a runtime analysis:

  words   lemma -> CEFR level, frequency, part of speech
  forms   surface form -> (lemma, tag)   [the reverse index]

Linguistic facts still come from a real morphological analyser, never a model.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from estnltk.vabamorf.morf import synthesize

from .config import DATA
from .morph import _readings, case_forms
from .wordlist import declines

# The 28 nominal case/number combinations. Object case needs sg g / sg p, but
# exporting all of them means the locative drills (loc-case) need no re-export.
NOUN_TAGS = (
    "sg n", "sg g", "sg p", "sg ill", "sg in", "sg el", "sg all", "sg ad",
    "sg abl", "sg tr", "sg ter", "sg es", "sg ab", "sg kom",
    "pl n", "pl g", "pl p", "pl ill", "pl in", "pl el", "pl all", "pl ad",
    "pl abl", "pl tr", "pl ter", "pl es", "pl ab", "pl kom",
)

# Verb forms that carry the irregular stems behind the `verb-form` error tag:
# present, past, participles, infinitives, conditional, imperative, impersonal.
VERB_TAGS = (
    "n", "d", "b", "me", "te", "vad",      # present personal
    "sin", "sid", "s", "sime", "site", "sid",  # past personal
    "nud", "tud", "takse", "ti",           # participles / impersonal
    "da", "ma", "ks", "ge", "gu",          # infinitives, conditional, imperative
)

EXPORT_SCHEMA = """
PRAGMA journal_mode=DELETE;

CREATE TABLE IF NOT EXISTS words (
    lemma       TEXT PRIMARY KEY,
    proficiency TEXT,
    freq_rank   INTEGER,
    pos         TEXT
);
CREATE INDEX IF NOT EXISTS idx_w_prof ON words(proficiency);

CREATE TABLE IF NOT EXISTS forms (
    form  TEXT NOT NULL,
    lemma TEXT NOT NULL,
    tag   TEXT NOT NULL,
    PRIMARY KEY (form, lemma, tag)
);
-- The lookup that replaces runtime morphological analysis.
CREATE INDEX IF NOT EXISTS idx_f_form  ON forms(form);
CREATE INDEX IF NOT EXISTS idx_f_lemma ON forms(lemma);

CREATE TABLE IF NOT EXISTS object_cases (
    lemma     TEXT PRIMARY KEY,
    genitive  TEXT NOT NULL,
    partitive TEXT NOT NULL,
    distinct_ INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_oc_distinct ON object_cases(distinct_);
"""


def _select_lemmas(
    src: sqlite3.Connection, max_freq_rank: int
) -> list[tuple[str, str | None, int | None, str | None]]:
    """Everything CEFR-tagged, plus the frequency head — what is taught plus what is
    met; the full 160k list is mostly proper nouns and technical vocabulary.
    """
    return list(
        src.execute(
            """SELECT word, proficiency, freq_rank, pos FROM words
               WHERE proficiency IS NOT NULL
                  OR (freq_rank IS NOT NULL AND freq_rank BETWEEN 1 AND ?)
               ORDER BY word""",
            (max_freq_rank,),
        )
    )


def _tags_for(pos: str | None) -> tuple[str, ...]:
    tags = set()
    for tag in (pos or "s").split(","):
        if tag == "v":
            tags.update(VERB_TAGS)
        else:  # nouns, adjectives, numerals, pronouns all decline
            tags.update(NOUN_TAGS)
    return tuple(sorted(tags))


def _reads_back(form: str, lemma: str, tag: str) -> bool:
    """Whether Vabamorf, analysing `form`, finds `lemma` in `tag`.

    `synthesize` answers every request: an adverb gets fourteen "plural cases"
    that are all `kus`, and a postposition a plural (`aadressilideta`). About
    one generated row in five is such an invention; a form Vabamorf cannot read
    back is not one the card may name.
    """
    return any(l.casefold() == lemma.casefold() and f == tag
               for l, f in _readings(form))


def export(
    src: sqlite3.Connection,
    dest_path: Path | None = None,
    max_freq_rank: int = 25_000,
) -> dict[str, int]:
    """Write the dataset. Idempotent — overwrites any previous build."""
    dest_path = Path(dest_path or DATA / "edge.db")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()

    dest = sqlite3.connect(dest_path)
    dest.executescript(EXPORT_SCHEMA)

    lemmas = _select_lemmas(src, max_freq_rank)
    stats = {"lemmas": len(lemmas), "forms": 0, "object_cases": 0, "distinct": 0}

    word_rows, form_rows, oc_rows = [], [], []
    for lemma, prof, freq, pos in lemmas:
        word_rows.append((lemma, prof, freq, pos))
        seen: set[tuple[str, str]] = set()
        for tag in _tags_for(pos):
            for form in synthesize(lemma, tag) or []:
                if (form, tag) not in seen and _reads_back(form, lemma, tag):
                    seen.add((form, tag))
                    form_rows.append((form, lemma, tag))
        # A word with no form that reads back (`kus`, `aga`, `aitäh`, `WC`) is
        # still a word: it is listed once, as itself, with no invented tag.
        if not seen:
            form_rows.append((lemma.lower(), lemma, ""))

        # Only words that decline get a citation form: Vabamorf synthesises paradigms for
        # adverbs and imperatives too (`alguses` → `algusese`).
        if declines(pos):
            # `morph.case_forms`, not a raw synthesise: it round-trips candidates and requires
            # one survivor, so homographs (`kool`/`koola`, `reis`) are refused rather than
            # given another word's paradigm.
            forms = case_forms(lemma)
            if forms:
                gen, par = forms["genitive"], forms["partitive"]
                oc_rows.append((lemma, gen, par, int(gen != par)))

    with dest:
        dest.executemany("INSERT OR REPLACE INTO words VALUES (?,?,?,?)", word_rows)
        dest.executemany("INSERT OR IGNORE INTO forms VALUES (?,?,?)", form_rows)
        dest.executemany(
            "INSERT OR REPLACE INTO object_cases VALUES (?,?,?,?)", oc_rows
        )

    stats["forms"] = len(form_rows)
    stats["object_cases"] = len(oc_rows)
    stats["distinct"] = sum(r[3] for r in oc_rows)
    stats["bytes"] = dest_path.stat().st_size
    dest.close()
    return stats
