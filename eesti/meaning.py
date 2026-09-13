"""Which Russian a word gets, stated once for every place the app shows one.

Four sources can answer, each kept where it lives, none writing another's:

1. `seed`    — `data/seed_glossary.tsv`, 294 glosses written for the words the
               drills use most, read from the shipped file
2. live     — the live dictionary's gloss, `word_gloss` in `vocab.db`: EKI's
               Ekilex API (`ekilex`) with a key, the Sõnaveeb mirror
               (`sonapi`) without — asked on the word card; everywhere else,
               what is already stored
3. `eki-evs` — EKI's Estonian–Russian dictionary, `evs_gloss`, offline
4. `eki-har` — EKI's education terms, `har_gloss`, offline

**Why live outranks EKI's files.** The downloads are snapshots — EVS as
exported, PSV from 2014, the level list from 2018 — and Sõnaveeb is EKI's
database as it is today. The files answer when the live source has nothing,
cannot be asked, or has not been asked yet: every flow but the word card only
reads what is already stored.

**Why the seed outranks EKI.** Measured 2026-09-13: EVS covers 287 of the 294,
shares a translation with the seed on 277, and puts a different word first on
45. Where they differ, EVS's first line is the dictionary's first *sense*, not
the one a learner drilling A2 means: `kohus` → "долг" where the drill means
"суд", `jõudma` → "мочь" for "успевать, добираться", `arvuti` →
"вычислительная машина" where everyone says "компьютер". The seed was written
for exactly those words; EKI covers the other 60 000. Seven seed words EVS has
no entry for at all (`päike`, `riided`…).

The order was first written into the word card, then copied into the drill
glosses and the graded-answer gloss, and missing from the vocabulary list and
the review flashcards — five places, three of them in step. That is the shape
this codebase keeps paying for (`docs/lessons.md`, *Derived, never
hand-maintained*), so every flow now asks here.

The Estonian definition has its own order (PSV → Sõnaveeb → VSL → EKSS) and is
only ever shown on the word card, so it stays in `api/grammar._meaning`.
"""

from __future__ import annotations

import sqlite3

from functools import lru_cache

from . import evs, har

#: How many translations a flow shows. One number, so the card, the list and a
#: flashcard cannot disagree about what a word means.
SHOWN = 3


@lru_cache(maxsize=1)
def _seed() -> dict[str, list[str]]:
    """The shipped glossary, read once. A file in the image, not state."""
    from .gloss import SEED

    out: dict[str, list[str]] = {}
    if SEED.exists():
        for line in SEED.read_text(encoding="utf-8").splitlines():
            lemma, _, ru = line.strip().partition("\t")
            if lemma and ru.strip() and not lemma.startswith("#"):
                out[lemma.strip()] = [ru.strip()]
    return out


def russian(words: sqlite3.Connection, lemma: str,
            sonaveeb: tuple[str, ...] | list[str] = (),
            live_source: str = "sonapi",
            beside_its_definition: bool = False) -> tuple[list[str], str | None]:
    """`(translations, source id)` for one lemma; `([], None)` if nobody knows.

    `sonaveeb` is whatever the caller already has from the live dictionary — a
    fresh answer on the word card, a stored one elsewhere. Never fetches.

    `beside_its_definition` is the word card's case: the live dictionary's
    definition is on screen, so its Russian goes first, or the card describes
    two words. Measured with Ekilex, 2026-09-13: `kohus` showed EKI's
    definition of "duty" beside the seed's "суд" (a court) — the seed names the
    sense the drills use, which is right for a drill and wrong beside a
    definition of the other homonym.
    """
    if beside_its_definition and sonaveeb:
        return list(sonaveeb[:SHOWN]), live_source
    seeded = _seed().get(lemma)
    if seeded:
        return list(seeded), "seed"
    if sonaveeb:
        return list(sonaveeb[:SHOWN]), live_source
    offline = evs.russian(words, lemma)
    if offline:
        return list(offline[:SHOWN]), "eki-evs"
    terms = har.russian(words, lemma)
    if terms:
        return list(terms[:SHOWN]), "eki-har"
    return [], None


def russian_many(words: sqlite3.Connection, store: sqlite3.Connection | None,
                 lemmas: list[str]) -> dict[str, list[str]]:
    """`russian()` for a page of lemmas, from local tables only. Omits unknowns."""
    from . import gloss

    wanted = [l for l in dict.fromkeys(lemmas) if l]
    stored: dict[str, list[str]] = {}
    if store is not None and wanted:
        try:
            stored = {k: list(g.russian) for k, g in
                      gloss.stored_many(store, wanted).items() if g.russian}
        except sqlite3.Error:
            stored = {}
    offline = evs.russian_many(words, wanted)
    out: dict[str, list[str]] = {}
    for lemma in wanted:
        if lemma in offline and lemma not in _seed() and lemma not in stored:
            found = offline[lemma][:SHOWN]
        else:
            found, _ = russian(words, lemma, stored.get(lemma, ()))
        if found:
            out[lemma] = found
    return out
