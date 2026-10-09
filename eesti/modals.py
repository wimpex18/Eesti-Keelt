"""Which infinitive a modal verb takes, read off EKI EVS's phrases.

*võin minna*, *saan minna*, *tohin minna*, but *pean minema*: the governing
verb decides between the **da**- and the **ma**-infinitive, not the meaning.
The mapping is not written down here; it is what EVS's example phrases show
(`governed`): every phrase in which a word Vabamorf can read only as one of
`GOVERNORS` stands right before a word it reads only as an infinitive.

Left out, because the infinitive there is not the modal's:

- an idiom EVS lists (*hakkama saama*: `saan hakkama` is one unit, `evs.idioms`);
- a chain (*võib lõhkuma minna*: *lõhkuma* belongs to *minna*);
- *saama* + *olema*, the *saama*-future (EKK SÜ 28), which is never graded.

A modal EVS still shows with both infinitives is dropped rather than drilled
with one of them. An item blanks the infinitive in the phrase and asks which
one, credited to EVS.
"""

from __future__ import annotations

import os
import random
import sqlite3
from dataclasses import dataclass

from estnltk.vabamorf.morf import synthesize

from .config import LEVELS
from .conjugation import (PHRASE_WORDS, VerbDrill, adjacent, answer_for, blank, forms,
                          reading, verb_levels, words_in)

GOVERNORS = ("võima", "saama", "tohtima", "pidama")
INFINITIVES = ("ma", "da")

#: Vabamorf tags a governing verb may stand in, to find its written forms.
_TAGS = ("n", "d", "b", "me", "te", "vad", "sin", "sid", "s", "sime", "site",
         "ks", "ksin", "ksid", "ksime", "ksite", "o", "ge", "gu", "neg o",
         "nud", "vat", "takse", "ti", "ta", "tud", "ma", "da", "des")

#: The infinitive's name, and how a Russian speaker knows it.
_NAMES = {"ma": "ma-tegevusnimi (ma-инфинитив)", "da": "da-tegevusnimi (da-инфинитив)"}


@dataclass(frozen=True)
class Pair:
    """One governing verb right before its infinitive, in one EVS phrase."""

    phrase: str
    governor: str
    tags: frozenset[str]     # the governing word's readings (`b`, `ks`…)
    lemma: str               # the infinitive's verb
    form: str                # `ma` or `da`
    word: str                # the infinitive as written
    start: int
    end: int


def _governor(word: str, governors: tuple[str, ...]) -> tuple[str, frozenset[str]] | None:
    """The governing verb a word can only be, with its tags; None when Vabamorf
    reads it as anything else too (*pead* is also *pea*, "heads")."""
    from .morph import _readings

    found = _readings(word.casefold())
    lemmas = {lemma for lemma, _ in found}
    if len(lemmas) != 1 or not lemmas <= set(governors):
        return None
    return lemmas.pop(), frozenset(tag for _, tag in found)


def _infinitive(word: str) -> bool:
    from .morph import _readings

    return any(tag in INFINITIVES for _, tag in _readings(word.casefold()))


_CACHE: dict[tuple, list[Pair]] = {}


def _key(conn: sqlite3.Connection, governors: tuple[str, ...]) -> tuple | None:
    """The cache key for one words database, or None for an unnamed one."""
    try:
        name = conn.execute("PRAGMA database_list").fetchone()[2]
        rows = conn.execute("SELECT COUNT(*) FROM evs_example").fetchone()[0]
    except (sqlite3.Error, TypeError):
        return None
    if not name or not os.path.exists(name):
        return None
    return name, os.path.getmtime(name), rows, governors


def pairs(conn: sqlite3.Connection, governors: tuple[str, ...] = GOVERNORS) -> list[Pair]:
    """Every governing verb right before its infinitive in EVS's example
    phrases, in EKI's order; `[]` before the import. Read once per database."""
    key = _key(conn, governors)
    if key is not None and key in _CACHE:
        return _CACHE[key]
    from .evs import idioms, phrases

    together = idioms(conn)
    surfaces = {f.casefold() for g in governors for t in _TAGS
                for f in (synthesize(g, t) or [])}
    out: list[Pair] = []
    for phrase in phrases(conn, 2, 20):
        text = phrase.estonian
        spans = words_in(text)
        for i, here in enumerate(spans[:-1]):
            if here[0].casefold() not in surfaces:
                continue
            found = _governor(here[0], governors)
            after = spans[i + 1]
            infinitive = reading(after[0])
            if (found is None or infinitive is None or infinitive[1] not in INFINITIVES
                    or not adjacent(text, here, after)):
                continue
            governor, tags = found
            lemma, form = infinitive
            chained = (i + 2 < len(spans) and adjacent(text, after, spans[i + 2])
                       and _infinitive(spans[i + 2][0]))
            if (chained or f"{lemma} {governor}" in together
                    or (governor == "saama" and lemma == "olema")):
                continue
            out.append(Pair(text, governor, tags, lemma, form, after[0], *after[1:]))
    if key is not None:
        _CACHE[key] = out
    return out


def governed(conn: sqlite3.Connection,
             governors: tuple[str, ...] = GOVERNORS) -> dict[str, str]:
    """`{governing verb: "ma" | "da"}` as EVS's phrases show it. A verb they
    show with both, or not at all, is left out."""
    shown: dict[str, set[str]] = {}
    for pair in pairs(conn, governors):
        shown.setdefault(pair.governor, set()).add(pair.form)
    return {g: next(iter(f)) for g, f in shown.items() if len(f) == 1}


def other_infinitive(lemma: str, form: str) -> str | None:
    """The infinitive the learner might reach for instead."""
    if form == "da":
        return lemma
    made = forms(lemma, "da")
    return made[0] if made else None


def item(pair: Pair, level: str | None, topic: str, why_ru: str) -> VerbDrill | None:
    """The gap at the infinitive of one pair, or None when the two infinitives
    coincide."""
    from .evs import SOURCE_ID

    answer = answer_for(pair.lemma, pair.form, pair.word)
    wrong = other_infinitive(pair.lemma, pair.form)
    if not wrong or wrong.casefold() in answer.casefold().split(" ~ "):
        return None
    return VerbDrill(
        prompt=blank(pair.phrase, pair.start, pair.end), answer=answer,
        distractor=wrong, lemma=pair.lemma, tag=pair.form,
        form_et="ma- või da-tegevusnimi", rule="modaal" if topic == "ma-da-inf" else "hakkama",
        why_ru=f"{why_ru} *{pair.lemma}* → **{pair.word}**, не *{wrong}*.",
        topic=topic, level=level, source_id=SOURCE_ID)


def drills(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
    count: int = 10,
    seed: int | None = None,
    only: frozenset[str] | None = None,
) -> list[VerbDrill]:
    """`ma-da-inf` gaps after a modal verb, in the infinitive EVS shows it with;
    one per phrase and per modal and verb, the infinitive's verb at `levels`."""
    if count <= 0:
        return []
    takes = governed(conn)
    verbs = verb_levels(conn, levels, only)
    pool = [p for p in pairs(conn)
            if takes.get(p.governor) == p.form and p.lemma in verbs
            and len(p.phrase.split()) <= PHRASE_WORDS[1]]
    random.Random(seed).shuffle(pool)
    out: list[VerbDrill] = []
    seen: set = set()
    for pair in pool:
        if len(out) >= count:
            break
        if pair.phrase in seen or (pair.governor, pair.lemma) in seen:
            continue
        why = (f"Какой инфинитив — решает управляющий глагол. После **{pair.governor}** "
               f"— {_NAMES[pair.form]}: так во всех фразах EKI EVS с этим глаголом.")
        made = item(pair, verbs[pair.lemma], "ma-da-inf", why)
        if made:
            out.append(made)
            seen |= {pair.phrase, (pair.governor, pair.lemma)}
    return out
