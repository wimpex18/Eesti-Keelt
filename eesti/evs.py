"""*Eesti-vene sõnaraamat* — Russian for an Estonian word, without a network call.

EKI's Estonian–Russian dictionary (CC BY 4.0, `deploy/eki/`): about 60 000
lemmas with Russian, so a word card has Russian offline, over budget, or with
the live dictionary down.

Kept: headword, part of speech, at most `MAX_RUSSIAN` translations. Dropped:
Russian grammar notes, government (`vrek`), example phrases, and archaic (`van`)
translations.

**Order:** EKI's order within an article, neutral before labelled; across
homonyms, the word with the most senses leads (`_merge`).

**Storage:** `evs_gloss` in the words database (reference data; `vocab.db` is
learner state). Precedence is in `meaning.py`: seed, live dictionary, EVS, HAR.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import ekixml

#: A word card shows three; five leaves the drill glosses room without turning
#: a reminder into an entry.
MAX_RUSSIAN = 5

#: Same separator as `gloss.py` and `psv.py`.
SEP = "\x1f"

#: EKI's style label for an obsolete translation, dropped outright.
ARCHAIC = "van"

#: Style labels other than archaic (`kõnek`, `madalk`, `piltl`, `hlv`, `murd`…):
#: kept, but a labelled translation never precedes a neutral one.


@dataclass(frozen=True)
class Entry:
    lemma: str
    pos: str | None
    russian: tuple[str, ...]
    #: EKI's inflection type (`mt`), the muuttüüp a word card shows: `lugema`
    #: 28, `jätkuma` 27 — the numbers Sõnaveeb returns for the same words.
    inflection_type: str | None = None


def _labels(node) -> set[str]:
    """Style labels that mark a translation. `l="ka"` means *also* figurative etc., so
    the translation itself is ordinary and not counted as labelled.
    """
    return {ekixml.text(s) for s in node.findall("s") if s.get("l") != "ka"}


#: Labels that keep a translation last wherever it is (pejorative, vulgar,
#: low-register, slang, dialect, rare, ironic, jocular, poetic). Milder ones
#: (`kõnek`, `piltl`…) may stand in the main sense.
STRONG = {"hlv", "vulg", "madalk", "släng", "murd", "hrv", "iroon", "nlj", "luulek"}


def _article(article) -> tuple[int, list[str]]:
    """(number of senses, translations) in the order a learner needs them.

    1. two from the main sense (EKI's first `tp`), neutral then mildly labelled —
       `poiss` → мальчик, мальчишка;
    2. the neutral translations of the other senses, in EKI's order;
    3. the rest, strongly labelled last. Archaic translations and prefix forms are
       dropped.
    """
    main, main_labelled, rest_plain, rest_labelled, strong = [], [], [], [], []
    senses = 0
    for index, tp in enumerate(article.findall("S/tp") or [article]):
        for tg in tp.iter("tg"):
            found = False
            sense_labels = set().union(*(_labels(dg) for dg in tg.findall("dg")))
            if ARCHAIC in sense_labels:
                continue
            for xp in tg.findall("xp"):
                if xp.get(ekixml.XML_LANG) != "ru":
                    continue
                for xg in xp.findall("xg"):
                    labels = _labels(xg) | sense_labels
                    word = ekixml.russian(xg.find("x"))
                    # `_` is EVS saying "no single-word Russian; see the phrases".
                    # A prefix (`еже-` for `iga`) is how a compound translates,
                    # not what the word means on its own.
                    if ARCHAIC in labels or not word or word == "_" or word.endswith("-"):
                        continue
                    found = True
                    if labels & STRONG:
                        strong.append(word)
                    elif index == 0:
                        (main_labelled if labels else main).append(word)
                    elif labels:
                        rest_labelled.append(word)
                    else:
                        rest_plain.append(word)
            senses += found
    # The main sense leads with two, so a run of diminutives (`tüdruk`:
    # девочка, девчушка, девчурка) cannot push the second sense (девушка) off
    # a three-slot card.
    main = main + main_labelled
    return senses, main[:2] + rest_plain + main[2:] + rest_labelled + strong


def _inflection_type(raw: str) -> str | None:
    """EVS's `mt` in the form the card shows: zero padding removed (`02` → `2`), two
    paradigms as `11 / 9`, and None when EKI marks the type unsure (`?`), so the
    card asks the live dictionary instead.
    """
    if not raw or "?" in raw:
        return None
    parts = [p.strip().lstrip("0") or "0" for p in raw.split("_&_")]
    return " / ".join(parts) if all(p.isdigit() for p in parts) else None


def _merge(articles: list[tuple[int, list[str]]]) -> tuple[str, ...]:
    """One list for a lemma with several homonym articles: the article with the most
    senses supplies the first two translations (`suu` the mouth), then each other
    homonym gets its first (`iga` still shows "каждый").
    """
    ranked = [words for _, words in sorted(articles, key=lambda a: -a[0]) if words]
    if not ranked:
        return ()
    order = ranked[0][:2] + [w[0] for w in ranked[1:]] + ranked[0][2:] \
        + [x for w in ranked[1:] for x in w[1:]]
    return tuple(dict.fromkeys(order))[:MAX_RUSSIAN]


def parse(path: Path | str) -> list[Entry]:
    """One entry per lemma, homonyms merged, with at least one translation."""
    articles: dict[str, list[tuple[int, list[str]]]] = {}
    pos: dict[str, str | None] = {}
    types: dict[str, str | None] = {}
    for article in ekixml.articles(path):
        lemmas = ekixml.headwords(article)
        if not lemmas:
            continue
        senses, words = _article(article)
        if not words:
            continue
        for lemma in lemmas:
            articles.setdefault(lemma, []).append((senses, words))
            if lemma not in pos:
                first = article.find("P/mg/sl")
                pos[lemma] = ekixml.text(first) or None
                types[lemma] = _inflection_type(ekixml.text(article.find("P/mg/grg/mt")))
    return [Entry(lemma, pos[lemma], _merge(a), types[lemma]) for lemma, a in articles.items()]


SCHEMA = """
-- EKI's Estonian-Russian dictionary, in the words database: reference data.
CREATE TABLE IF NOT EXISTS evs_gloss (
    lemma   TEXT PRIMARY KEY,
    pos     TEXT,
    russian TEXT NOT NULL      -- \x1f-joined, like `word_gloss.russian`
);
"""


def store(conn: sqlite3.Connection, entries: list[Entry]) -> dict[str, int]:
    """Replace the table's contents with `entries`. Idempotent."""
    conn.executescript(SCHEMA)
    ekixml.ensure_column(conn, "evs_gloss", "inflection_type")
    with conn:
        conn.execute("DELETE FROM evs_gloss")
        conn.executemany(
            "INSERT INTO evs_gloss (lemma, pos, russian, inflection_type) VALUES (?,?,?,?)",
            [(e.lemma, e.pos, SEP.join(e.russian), e.inflection_type) for e in entries],
        )
    return {"entries": len(entries)}


def russian(conn: sqlite3.Connection, lemma: str) -> tuple[str, ...]:
    """The Russian for one lemma, or `()`. A missing table is `()` too."""
    try:
        row = conn.execute(
            "SELECT russian FROM evs_gloss WHERE lemma = ?", (lemma,)).fetchone()
    except sqlite3.Error:
        return ()
    return tuple(r for r in row[0].split(SEP) if r) if row else ()


def russian_many(conn: sqlite3.Connection, lemmas: list[str]) -> dict[str, list[str]]:
    """`russian()` for several lemmas in one query; absent lemmas are omitted."""
    wanted = sorted({l for l in lemmas if l})
    if not wanted:
        return {}
    try:
        rows = conn.execute(
            f"SELECT lemma, russian FROM evs_gloss WHERE lemma IN "
            f"({','.join('?' * len(wanted))})", wanted).fetchall()
    except sqlite3.Error:
        return {}
    return {r[0]: [w for w in r[1].split(SEP) if w] for r in rows}


def inflection_type(conn: sqlite3.Connection, lemma: str) -> str | None:
    """EKI's muuttüüp for a lemma, or None — also None on an older table."""
    try:
        row = conn.execute("SELECT inflection_type FROM evs_gloss WHERE lemma = ?",
                           (lemma,)).fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row and row[0] else None


def imported(conn: sqlite3.Connection) -> int:
    try:
        return conn.execute("SELECT COUNT(*) FROM evs_gloss").fetchone()[0]
    except sqlite3.Error:
        return 0
