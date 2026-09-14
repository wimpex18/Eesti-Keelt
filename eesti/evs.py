"""*Eesti-vene sõnaraamat* — Russian for an Estonian word, without a network call.

## The gap this fills

`gloss.py` gets Russian from Sõnaveeb, one live request per word, capped by a
daily budget and never in bulk. `data/seed_glossary.tsv` covers the 294 words
drills use most. Everything else a learner clicks while reading had no Russian
until Sõnaveeb was asked — and none at all offline, over budget, or with
Sõnaveeb down.

EKI publish the Estonian–Russian dictionary for download under CC BY 4.0:
70 882 articles, 60 672 lemmas with at least one usable Russian translation
(measured 2026-09-13 on `evs_EKI_CCBY40.xml`). So the Russian a word card needs
is a file, not a request.

## What is kept

Headword, part of speech, and at most `MAX_RUSSIAN` translations. Not the
Russian inflection notes, aspect pairs, government (`vrek`) or the translated
example phrases — a word card is a reminder, and Sõnaveeb is one link away for
the rest. Translations labelled archaic (`van`) are dropped: a learner at A2
should not meet `благой` as the meaning of `hea`.

## Which translations come first

EKI's own order within an article, neutral translations before labelled ones
(`kõnek`, `madalk`, `hlv`… — see `_labels`). Across homonym articles, the word
with the most senses leads and every other homonym gets one early slot — see
`_merge`. An earlier breadth-first order across *senses* put `poiss`'s
interjection sense, "смотри", third on the card.

## Where it lives

`evs_gloss` in the words database, beside `psv_gloss` and for the same reason:
reference data, identical for everybody, and `vocab.db` is replaced whole by a
state-snapshot restore. It never writes `word_gloss` — Sõnaveeb's answers stay
Sõnaveeb's — so the preference between the two is stated where they are read,
in `meaning.py`: after the hand-written seed and the live dictionary, before HAR.

The file's shape is not its schema's; `ekixml` has what was measured.
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

#: Every *other* style label (`evs_tyybid.xsd`, `s_tyyp`): colloquial `kõnek`
#: on 16 907 translations, low-register `madalk` 3 677, figurative `piltl`,
#: pejorative `hlv`, dialect `murd`, slang, vulgar… None is
#: dropped — a word whose only Russian is colloquial still needs it — but a
#: labelled translation or sense never comes before a neutral one, so the first
#: thing a learner reads for a word is the word as it is normally used.


@dataclass(frozen=True)
class Entry:
    lemma: str
    pos: str | None
    russian: tuple[str, ...]
    #: EKI's inflection type (`mt`), the muuttüüp a word card shows: `lugema`
    #: 28, `jätkuma` 27 — the numbers Sõnaveeb returns for the same words.
    inflection_type: str | None = None


def _labels(node) -> set[str]:
    """Style labels that mark a translation. `l="ka"` means *also* figurative,
    colloquial… — the translation itself is ordinary, so it does not count.
    2 340 labels carry `ka`; counting them dropped `читать`
    from `lugema`."""
    return {ekixml.text(s) for s in node.findall("s") if s.get("l") != "ka"}


#: Labels that keep a translation last wherever it is. Milder ones (`kõnek`,
#: `piltl`, `dem`, `hellitl`…) may stand in the main sense: `мальчишка` is still
#: "boy". These may not: pejorative, vulgar, low-register, slang, dialect,
#: rare, ironic, jocular, poetic.
STRONG = {"hlv", "vulg", "madalk", "släng", "murd", "hrv", "iroon", "nlj", "luulek"}


def _article(article) -> tuple[int, list[str]]:
    """(number of senses, translations) in the order a learner needs them.

    1. two from the main sense (EKI's first `tp`), neutral then mildly
       labelled — `poiss` → мальчик, мальчишка: both "boy";
    2. the neutral translations of the other senses, in EKI's order;
    3. the rest of the main sense, then everything else, strongly labelled
       last. Archaic translations and prefix forms are dropped.

    Taking one neutral translation from every sense in turn put `poiss`'s
    interjection sense ("смотри") third on the card, ahead of every other
    word for "boy".
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
    """EVS's `mt` in the form the card shows and Sõnaveeb returns.

    42 204 single types, zero-padded (`02`, `17`);
    1 682 words with two paradigms (`11_&_09`); 1 261 of those marked `?` —
    EKI unsure of the type. Padded becomes `2`, a pair `11 / 9`, and an unsure
    one None: a muuttüüp a learner copies into Sõnaveeb must not be a guess,
    and None makes the card ask Sõnaveeb instead.
    """
    if not raw or "?" in raw:
        return None
    parts = [p.strip().lstrip("0") or "0" for p in raw.split("_&_")]
    return " / ".join(parts) if all(p.isdigit() for p in parts) else None


def _merge(articles: list[tuple[int, list[str]]]) -> tuple[str, ...]:
    """One list for a lemma with several homonym articles.

    The article with the most senses is the word a learner means (`suu` the
    mouth, 12 senses, not the sou, 1; `pea` the head, not "soon"), and it
    supplies the first two translations. Each other homonym then gets its
    first, so `iga` still shows "каждый" beside "возраст" on a three-slot card.
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
