"""Which Russian a word gets, stated once for every place the app shows one.

1. `seed`    — `data/seed_glossary.tsv`, hand-written glosses for the words
               drills use most
2. live      — `word_gloss` in `vocab.db`: EKI's Ekilex API (`ekilex`) with a
               key, the Sõnaveeb mirror (`sonapi`) without; asked on the word
               card, read from the store everywhere else
3. `eki-evs` — EKI's Estonian–Russian dictionary (`evs_gloss`), offline
4. `eki-har` — EKI's education terms (`har_gloss`), offline

**Live outranks EKI's files:** the files are snapshots; the live dictionary is
EKI's current data. **The seed outranks both** outside the word card: it names
the sense the drills use (`kohus` → "суд", where EVS's first sense is "долг").

Used by the word card, the Sõnavara list, drill glosses, the graded-answer gloss
and review flashcards. The Estonian definition order (PSV → live → VSL → EKSS)
lives in `api/grammar._meaning`.
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

    `sonaveeb` is what the caller already has from the live dictionary; this never
    fetches. `beside_its_definition` is the word card's case: the live definition is
    on screen, so its Russian goes first — otherwise the seed's sense (`kohus`
    "суд") could sit beside a definition of the other homonym ("duty").
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
