"""Build-time export: turn Vabamorf's knowledge into a portable dataset.

Why this exists
---------------
The app is deployed on Cloudflare, and Cloudflare Workers run Python through
Pyodide/WebAssembly — which supports pure-Python and PyEmscripten wheels only.
Vabamorf is a compiled C++ extension, so **it cannot run at the edge**.

Rather than give up determinism, we move Vabamorf to *build time*. It generates
every form we could need, labelled with its case, and the result ships as data.
The edge runtime then needs no morphology engine at all — just indexed lookups.

This keeps the property that mattered in the first place: linguistic facts come
from a real morphological analyser, never from a language model.

Two tables carry it:

  words   lemma -> CEFR level, frequency, part of speech
  forms   surface form -> (lemma, tag)   [the reverse index]

`forms` is what replaces runtime analysis. Vabamorf answers "what case is
`raamatut`?"; a unique index on `form` answers the same question with a SELECT.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from estnltk.vabamorf.morf import synthesize

from .config import DATA
from .morph import case_forms
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
    """Everything CEFR-tagged, plus the frequency head.

    CEFR-tagged words are what a learner is taught; the frequency head is what
    they will actually meet in the wild. Exporting all 160k lemmas would work
    but mostly ships proper nouns and technical vocabulary nobody at B1 writes.
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


def export(
    src: sqlite3.Connection,
    dest_path: Path | None = None,
    max_freq_rank: int = 25_000,
) -> dict[str, int]:
    """Write the edge-ready dataset. Idempotent — overwrites any previous build."""
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
                if (form, tag) not in seen:
                    seen.add((form, tag))
                    form_rows.append((form, lemma, tag))

        # Only words that decline get a citation form.
        #
        # Vabamorf refuses a genitive for a verb, so verbs never reached this
        # table -- and that quietly suggested the synthesiser would refuse for
        # anything else that has no paradigm. It does not. Asked for the
        # genitive of the adverb `alguses` it answers `algusese`; of `dna`,
        # `dnad`; of the imperative `õpi`, a full declension. 319 of 7 256
        # drillable entries were invented that way, and `/api/lookup` printed
        # them to the learner as confidently as `raamat, raamatu, raamatut`.
        #
        # `wordlist.nouns_at_level` already gated the *drill* path on part of
        # speech. This path never did, so the same job had two behaviours.
        if declines(pos):
            # `morph.case_forms`, not a raw synthesise.
            #
            # `next(iter(synthesize(...)))` takes whichever candidate Vabamorf
            # happens to list first, and for an ambiguous string that is often
            # a different word's paradigm. The table shipped `kool, koola,
            # koola` -- the declension of *koola*, cola, for the word "school"
            # -- and `reis, reie, reit`, which is *reis* the thigh rather than
            # *reis* the journey. `/api/lookup` printed both to the learner in
            # citation format.
            #
            # `case_forms` round-trips each candidate through analysis and
            # requires exactly one survivor, refusing when several read back.
            # Its docstring names `kool` and `reis` as the reason it exists.
            # This module reimplemented the naive version it replaced.
            #
            # Refusing costs entries -- `kolmas` has two genuinely attested
            # partitives, `kolmat` and `kolmandat` -- and that is the trade the
            # rule already makes everywhere else: no citation beats a wrong one.
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
