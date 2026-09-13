"""*Eesti keele põhisõnavara sõnastik* — definitions written for learners.

## The gap this fills, and why `sonapi` could not

`gloss.py` stores what Sõnaveeb says a word means. What Sõnaveeb says is the
**full EKI definition**, written for a native speaker consulting a dictionary:

    lugema  kirjalikku teksti sõnahaaval jälgima ja sõnu ning lauseid
            tõlgendades selle tähendust tajuma

That is an accurate definition and it is useless to somebody at A2, who now has
four words to look up instead of one. It is the reason *Keeleõppija Sõnaveeb*
exists — about 7 000 words with their main senses restated simply — and the
reason an earlier pass of this project wrote that material off: reaching it
meant a second client against the site whose maintainers ask not to be
batch-requested.

**EKI publishes the same thing for download, under CC BY 4.0.** The *Eesti
keele põhisõnavara sõnastik* (2014) is roughly 6 000 basic words with
learner-level definitions and usage examples, and EKI's own licence page says
the material may be processed and presented in any way needed — an app
included — provided the attribution is kept and the changes described. So the
answer to "how do we get the learner dictionary" was never a scraper. It was a
file.

## Where it lives, and why not with the glosses

**The words database, not `vocab.db`.** That was the first design and it was
wrong in the one environment that matters.

`vocab.db` is carried by the **state snapshot** — it holds what this learner
has met and how they are doing — and a restore replaces the file wholesale.
Cloud Run scales to zero, so a cold start and therefore a restore is the normal
path, not an exceptional one. PSV definitions baked into that file would have
survived exactly until the first restore and then vanished, permanently, with
nothing saying so.

PSV is not learner state. It is **reference data**: six thousand dictionary
entries that are the same for everybody, no more personal than the word list or
the inflection tables. So it belongs where the rest of the reference data lives
— `eesti.db`, built into the image, rebuilt by every deploy — and the snapshot
carries only what is actually the learner's.

That also dissolved a trap rather than working around it. When these
definitions filled `word_gloss` rows, a PSV-covered word looked *already
looked up*, so `remember()` would have stopped asking Sõnaveeb and the six
thousand commonest words would have lost their Russian translation for ever.
Keeping PSV in its own table means `word_gloss` is untouched, every word is
still enriched on demand, and there is no baseline-versus-ceiling rule to get
right.

## Two definitions, two tables

A PSV definition and a Sõnaveeb definition are **different claims about
different audiences**, not two guesses at one claim, so they do not share a
column — the same rule that keeps `level` and `band` apart.

`psv_gloss.definition` holds PSV's, in the words database;
`word_gloss.definition` holds Sõnaveeb's, in the learner's. Neither can
overwrite the other because neither knows about the other — the preference is
expressed once, where the two are read together, and the whole value of the
learner-level wording is that the native-level wording does not replace it.

## Not fetched from here

Same posture as `cli import-levels`: EKI serves the file behind a page asking
who you are and what the material will be used in, which is a request worth
answering rather than stepping around. The learner downloads
`psv_EKI_CCBY40.xml` and names it. The filename is EKI's own and says the
licence out loud.

## The format, read from EKI's schema rather than guessed

`schema_psv.xsd` is published beside the data and was read on 2026-09-11:

    sr                      the dictionary
      A                     one article
        P/mg/m              märksõna — the headword
        S/tp/grg/sl         sõnaliik — part of speech
        S/tp/tg/dg/d        seletus — the definition
        S/tp/tg/ng/n        näide — a usage example

EKI warn on the same page that their XML **does not validate against that
schema** — editing metadata is stripped, and elements the schema marks required
can be absent. So this reads by descendant tag rather than by rigid path, and
treats every field except the headword as optional. A parser that insists on a
shape its own publisher says it does not have would fail on the real file and
pass on a fixture built from the schema.
"""

from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from . import ekixml

#: How many examples to keep per word. A word card is a reminder, not an entry
#: — the same reason `remember()` keeps three Russian glosses and not forty.
MAX_EXAMPLES = 3

#: The separator `gloss.py` already uses for its Russian list. Reused rather
#: than invented: one file, one convention, and `\x1f` cannot occur in EKI's
#: prose.
SEP = "\x1f"


@dataclass(frozen=True)
class Entry:
    """One article, flattened to what a word card can show."""

    lemma: str
    definition: str | None
    examples: tuple[str, ...]
    pos: str | None
    #: EKI's frequency tier, `sag`: 1 is commonest, absent is rarest. Decides
    #: which of two homonyms the one `psv_gloss` row per lemma belongs to.
    frequency: int | None = None
    #: What the word governs, as EKI write it (`kellele`, `mida teha`): the
    #: rektsioon a word card shows. 872 articles carry it, 609 of them verbs.
    rection: tuple[str, ...] = ()


def _first(node: ET.Element, tag: str) -> str:
    found = node.find(f".//{tag}")
    return ekixml.text(found) if found is not None else ""


def parse(path: Path | str) -> list[Entry]:
    """Read the dictionary. Articles without a headword are skipped, not raised.

    Through `ekixml.articles`, because the real file is not one XML document:
    no root, undeclared `c:` prefixes, one article per line. This function read
    it with `iterparse` until 2026-09-13 and failed on byte one of the real
    file, having passed every test against a fixture written from the schema.
    """
    entries: list[Entry] = []
    for article in ekixml.articles(path):
        examples = tuple(
            t for t in (ekixml.text(n) for n in article.iter("n")) if t
        )[:MAX_EXAMPLES]
        for lemma in ekixml.headwords(article):
            entries.append(Entry(
                lemma=lemma,
                definition=_first(article, "d") or None,
                examples=examples,
                pos=_first(article, "sl") or None,
                frequency=int(_first(article, "sag")) if _first(article, "sag").isdigit() else None,
                rection=_rection(article),
            ))
    return entries


#: `rliik` kinds a word card's rektsioon line means: the object (`obj`), a case
#: frame (`kn`), an infinitive (`inf`), a postposition phrase (`ks`) and an
#: adverbial question (`yld`, `kust`). Measured on the real file: kn 744,
#: obj 262, ks 200, inf 123, yld 93. `kla` (50) and `subj` (1) are clause and
#: subject frames, not what "rektsioon" shows beside a word, and are left out.
RECTION_KINDS = ("obj", "kn", "inf", "ks", "yld")


def _rection(article) -> tuple[str, ...]:
    found = [ekixml.text(r) for r in article.iter("rek") if r.get("rliik") in RECTION_KINDS]
    return tuple(dict.fromkeys(f for f in found if f))


def _one_per_lemma(entries: list[Entry]) -> list[Entry]:
    """The article a word card should show when EKI has several for a lemma.

    58 lemmas in the real file have two articles (`c:i="1"`, `c:i="2"`): `arm`
    is a scar and an amnesty, `iga` is an age and "every". The table holds one
    row per lemma, and an upsert in file order let the *last* article win — so
    `arm` meant amnesty. The commonest meaning wins now, by EKI's own `sag`
    tier; file order breaks a tie, which is EKI's homonym numbering.
    """
    best: dict[str, Entry] = {}
    for entry in entries:
        kept = best.get(entry.lemma)
        rank = entry.frequency if entry.frequency is not None else 99
        if kept is None or rank < (kept.frequency if kept.frequency is not None else 99):
            best[entry.lemma] = entry
    return list(best.values())


SCHEMA = """
-- EKI's learner dictionary, in the *words* database rather than the learner's.
--
-- Reference data: the same six thousand entries for everybody, no more
-- personal than the word list beside it. `vocab.db` is carried by the state
-- snapshot and a restore replaces it wholesale, so definitions kept there
-- would survive until the first cold start and then vanish. See the module
-- docstring.
CREATE TABLE IF NOT EXISTS psv_gloss (
    lemma      TEXT PRIMARY KEY,
    definition TEXT,
    examples   TEXT          -- \x1f-joined, like `word_gloss.russian`
);
"""


def store(conn: sqlite3.Connection, entries: list[Entry]) -> dict[str, int]:
    """Write the learner-level definitions into the words database.

    `conn` is a `wordlist.connect()` handle. Idempotent: re-importing a
    corrected file replaces what was there and adds nothing twice.
    """
    conn.executescript(SCHEMA)

    ekixml.ensure_column(conn, "psv_gloss", "rection")
    ekixml.ensure_column(conn, "psv_gloss", "pos")
    rows = [
        (e.lemma, e.definition, SEP.join(e.examples), ",".join(e.rection), e.pos)
        for e in _one_per_lemma(entries) if e.definition or e.examples
    ]
    stats = {"entries": len(entries), "written": len(rows)}
    if not rows:
        return stats
    with conn:
        # The file is the whole truth: a lemma a corrected file no longer has
        # must not survive in the table. Upserting alone kept seven headwords
        # under their old `Jäär_` spelling after the parser learnt to strip
        # the marker, beside the corrected `Jäär` rows.
        conn.execute("DELETE FROM psv_gloss")
        conn.executemany(
            "INSERT INTO psv_gloss (lemma, definition, examples, rection, pos)"
            " VALUES (?,?,?,?,?)",
            rows,
        )
    stats["with_examples"] = sum(1 for e in entries if e.examples)
    return stats


@dataclass(frozen=True)
class Gloss:
    """What PSV knows about one word."""

    definition: str | None
    examples: tuple[str, ...]
    rection: tuple[str, ...] = ()
    pos: str | None = None


def lookup(conn: sqlite3.Connection, lemma: str) -> Gloss | None:
    """EKI's learner-level entry for one word, or None.

    Absence is the common case and not an error: PSV covers about six thousand
    words and the app knows 160 316. A deployment that never imported the file
    has no table at all, and that is also None rather than a failure.
    """
    try:
        cursor = conn.execute("SELECT * FROM psv_gloss WHERE lemma = ?", (lemma,))
        found = cursor.fetchone()
    except sqlite3.Error:
        return None
    if found is None:
        return None
    row = dict(zip((d[0] for d in cursor.description), found))
    return Gloss(
        definition=row["definition"],
        examples=tuple(e for e in (row["examples"] or "").split(SEP) if e),
        rection=tuple(r for r in (row.get("rection") or "").split(",") if r),
        pos=row.get("pos"),
    )


def imported(conn: sqlite3.Connection) -> int:
    """How many words carry a learner-level definition. Zero is a valid answer."""
    try:
        return conn.execute("SELECT COUNT(*) FROM psv_gloss").fetchone()[0]
    except sqlite3.Error:
        return 0
