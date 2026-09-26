"""*Eesti-vene sõnaraamat* — Russian for an Estonian word, without a network call.

EKI's Estonian–Russian dictionary (CC BY 4.0, `deploy/eki/`): about 60 000
lemmas with Russian, so a word card has Russian offline, over budget, or with
the live dictionary down.

Kept: headword, part of speech, at most `MAX_RUSSIAN` translations. Dropped:
Russian grammar notes, government (`vrek`) and archaic (`van`) translations.
The example phrases, each with EKI's Russian, are kept apart in `evs_example`
(`examples()`): the word in use, not what it means.

**Order:** EKI's order within an article, neutral before labelled; across
homonyms, the word with the most senses leads (`_merge`).

**Storage:** `evs_gloss` in the words database (reference data; `vocab.db` is
learner state). Precedence is in `meaning.py`: seed, live dictionary, EVS, HAR.
"""

from __future__ import annotations

import re
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


# ---------------------------------------------------------------------------
# Question words: the Russian for one sense, not a merged list
# ---------------------------------------------------------------------------

#: EVS's parts of speech for a question word (`kus` adv, `kes` pron). A homonym
#: with another part of speech (`miks` the noun, "микс") is a different word.
QUESTION_POS = frozenset({"adv", "pron"})

QUESTION_SCHEMA = """
-- The Russian of a question word's first sense in EVS: the cue a küsisõnad
-- drill shows for its blank. Reference data, like `evs_gloss`.
CREATE TABLE IF NOT EXISTS evs_question (
    word    TEXT PRIMARY KEY,
    russian TEXT NOT NULL      -- \x1f-joined, EKI's order
);
"""


def _asks(tp, word: str) -> bool:
    """Whether EVS illustrates this sense with a direct question opening with
    `word` (`kus sa elad?`, `mitu last sul on?`).
    """
    for n in tp.findall("np/ng/n"):
        example = ekixml.text(n).casefold()
        if example.endswith("?") and re.match(rf"{re.escape(word)}\b", example):
            return True
    return False


def _question_sense(article, word: str) -> tuple[str, ...]:
    """The neutral Russian of the sense EVS uses in a question.

    `evs_gloss` merges every sense and homonym, which is right for a word card
    but not for a question word: `mitu` there leads with "несколько", and `kes`
    has the relative "который" beside "кто". Here the sense is the first `tp`
    whose own examples include a direct question opening with the word
    (`_asks`) — EVS's examples, not a judgement, say which sense a question
    uses — and within it the first sense group (`kes` → кто; the relative is
    the second group). A labelled translation is left out; no such sense, or
    nothing neutral in it, gives `()`.
    """
    tp = next((t for t in article.findall("S/tp") if _asks(t, word)), None)
    tg = tp.find("tg") if tp is not None else None
    if tg is None:
        return ()
    if set().union(*(_labels(dg) for dg in tg.findall("dg"))):
        return ()
    out: list[str] = []
    for xp in tg.findall("xp"):
        if xp.get(ekixml.XML_LANG) != "ru":
            continue
        for xg in xp.findall("xg"):
            ru = ekixml.russian(xg.find("x"))
            if _labels(xg) or not ru or ru == "_" or ru.endswith("-"):
                continue
            out.append(ru)
    return tuple(dict.fromkeys(out))


def question_senses(path: Path | str, words) -> dict[str, tuple[str, ...]]:
    """`{word: Russian}` for the question words EVS answers unambiguously.

    A word gets a cue only when EVS has **exactly one** article for it with a
    question word's part of speech (`QUESTION_POS`), and that article has a
    question sense with a neutral translation (`_question_sense`). Anything
    else — no article (`kelle`
    is a form of `kes`, not a headword; `kui palju` is two words), two
    candidate homonyms, a labelled sense — is left out: no cue rather than a
    guess. Case-insensitive on `words`; keys are lower-case.
    """
    wanted = {w.casefold() for w in words}
    found: dict[str, list[tuple[str, ...]]] = {}
    for article in ekixml.articles(path):
        lemmas = [l for l in ekixml.headwords(article) if l in wanted]
        if not lemmas:
            continue
        if ekixml.text(article.find("P/mg/sl")) not in QUESTION_POS:
            continue
        for lemma in lemmas:
            found.setdefault(lemma, []).append(_question_sense(article, lemma))
    return {w: senses[0] for w, senses in found.items()
            if len(senses) == 1 and senses[0]}


def store_questions(conn: sqlite3.Connection, cues: dict[str, tuple[str, ...]]) -> int:
    """Replace `evs_question` with `cues`. Idempotent."""
    conn.executescript(QUESTION_SCHEMA)
    with conn:
        conn.execute("DELETE FROM evs_question")
        conn.executemany("INSERT INTO evs_question (word, russian) VALUES (?,?)",
                         [(w, SEP.join(ru)) for w, ru in sorted(cues.items())])
    return len(cues)


def question_cues(conn: sqlite3.Connection | None) -> dict[str, tuple[str, ...]]:
    """Every stored cue; `{}` without a connection or before an import."""
    if conn is None:
        return {}
    try:
        rows = conn.execute("SELECT word, russian FROM evs_question").fetchall()
    except sqlite3.Error:
        return {}
    return {r[0]: tuple(x for x in r[1].split(SEP) if x) for r in rows}


def imported(conn: sqlite3.Connection) -> int:
    try:
        return conn.execute("SELECT COUNT(*) FROM evs_gloss").fetchone()[0]
    except sqlite3.Error:
        return 0


# ---------------------------------------------------------------------------
# Example phrases: the word in use, with EKI's Russian beside it
# ---------------------------------------------------------------------------

#: A slot the phrase leaves open, EVS's `<r>` (`kriitika <r>kelle/mille</r>
#: aadressil`) and its Russian `<xr>` (`в <xr>чей</xr> адрес`), is kept in
#: braces; the card sets it in italics. EVS itself never uses a brace.
SLOT = "{{{}}}"

#: How many alternative Russian renderings one phrase keeps (`olen sellest
#: kusagilt lugenud` → "я где-то читал об этом", then a colloquial variant).
MAX_RENDERINGS = 2


@dataclass(frozen=True)
class Example:
    lemma: str
    estonian: str
    russian: str


def _flatten(node, slot_tags: tuple[str, ...]) -> str:
    """A phrase as text, with its open slots in braces and EVS's marks gone."""
    out: list[str] = [node.text or ""]
    for child in node:
        inner = ekixml.text(child)
        if child.tag in slot_tags and inner:
            out.append(" " + SLOT.format(inner) + " ")
        elif child.tag not in ("s", "vrek"):
            out.append(inner)
        out.append(child.tail or "")
    shell = type(node)(node.tag)
    shell.text = "".join(out)
    return (ekixml.text(shell).replace('"', "").replace("*", "").replace("[]", "")
            .replace("{ ", "{").replace(" }", "}").strip())


def _example(ng) -> tuple[str, str] | None:
    """(Estonian, Russian) for one `ng`, or None when it is not a learner's example.

    Left out: a domain term (`aafrika elevant`, labelled *zool*, *aj*…, with its
    Latin name) — a dictionary of specialist names, not usage — and any phrase
    whose every Russian rendering is archaic or missing.
    """
    estonian = " / ".join(t for t in (_flatten(n, ("r",)) for n in ng.findall("n")) if t)
    if not estonian:
        return None
    renderings: list[str] = []
    for qnp in ng.findall("qnp"):
        if qnp.find("v") is not None or qnp.find("ld") is not None:
            return None
        for qng in qnp.findall("qng"):
            if qng.get(ekixml.XML_LANG) != "ru":
                continue
            if ARCHAIC in ({ekixml.text(s) for s in qng.findall("s")}
                           | {ekixml.text(s) for s in qnp.findall("s")}):
                continue
            ru = _flatten(qng.find("qn"), ("xr",)) if qng.find("qn") is not None else ""
            if ru and ru != "_":
                renderings.append(ru)
    renderings = list(dict.fromkeys(renderings))[:MAX_RENDERINGS]
    return (estonian, "; ".join(renderings)) if renderings else None


def parse_examples(path: Path | str) -> list[Example]:
    """Every example phrase EVS gives a lemma, in EKI's order: article by article,
    sense by sense. A phrase shared by two headwords of one article is kept for
    each.
    """
    out: list[Example] = []
    seen: set[tuple[str, str]] = set()
    for article in ekixml.articles(path):
        lemmas = ekixml.headwords(article)
        if not lemmas:
            continue
        for ng in article.findall("S/tp/np/ng"):
            found = _example(ng)
            if not found:
                continue
            for lemma in lemmas:
                if (lemma, found[0]) in seen:
                    continue
                seen.add((lemma, found[0]))
                out.append(Example(lemma, *found))
    return out


EXAMPLE_SCHEMA = """
-- EVS's example phrases with their Russian: reference data, like `evs_gloss`.
CREATE TABLE IF NOT EXISTS evs_example (
    lemma    TEXT NOT NULL,
    seq      INTEGER NOT NULL,   -- EKI's order within the lemma
    estonian TEXT NOT NULL,      -- open slots in braces (`SLOT`)
    russian  TEXT NOT NULL,
    PRIMARY KEY (lemma, seq)
) WITHOUT ROWID;
"""


def store_examples(conn: sqlite3.Connection, examples: list[Example]) -> int:
    """Replace `evs_example` with `examples`. Idempotent."""
    conn.executescript(EXAMPLE_SCHEMA)
    counter: dict[str, int] = {}

    def rows():
        for e in examples:
            counter[e.lemma] = counter.get(e.lemma, 0) + 1
            yield e.lemma, counter[e.lemma], e.estonian, e.russian

    with conn:
        conn.execute("DELETE FROM evs_example")
        conn.executemany(
            "INSERT INTO evs_example (lemma, seq, estonian, russian) VALUES (?,?,?,?)",
            rows())
    return len(examples)


#: The most phrases one card receives. EVS's longest list (`käima`) is 144.
MAX_EXAMPLES = 200


def examples(conn: sqlite3.Connection, lemma: str) -> list[dict]:
    """A lemma's phrases as `{"et", "ru"}`, in EKI's order; `[]` without the table."""
    try:
        rows = conn.execute(
            "SELECT estonian, russian FROM evs_example WHERE lemma = ? ORDER BY seq "
            "LIMIT ?", (lemma, MAX_EXAMPLES)).fetchall()
    except sqlite3.Error:
        return []
    return [{"et": et, "ru": ru} for et, ru in rows]
