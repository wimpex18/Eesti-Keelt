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

#: Provenance marker in `word_gloss.fetched`, alongside `seed` and a timestamp.
SOURCE = "psv"

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


def _text(node: ET.Element | None) -> str:
    """All text under a node, whitespace-collapsed.

    `itertext`, not `.text`: EKI marks emphasis and cross-references inside a
    definition, so `.text` stops at the first child and returns the sentence up
    to its first italic word.
    """
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def _first(node: ET.Element, tag: str) -> str:
    found = node.find(f".//{tag}")
    return _text(found) if found is not None else ""


def parse(path: Path | str) -> list[Entry]:
    """Read the dictionary. Articles without a headword are skipped, not raised.

    Streamed with `iterparse` and cleared as it goes: the file is one XML
    document holding every article, and reading it into a tree costs many times
    its size in memory for no benefit — nothing here needs two articles at once.
    """
    entries: list[Entry] = []
    for _, element in ET.iterparse(str(path), events=("end",)):
        if element.tag != "A":
            continue
        lemma = _first(element, "m")
        if lemma:
            examples = tuple(
                text for text in
                (_text(n) for n in element.findall(".//n"))
                if text
            )[:MAX_EXAMPLES]
            entries.append(Entry(
                lemma=lemma,
                definition=_first(element, "d") or None,
                examples=examples,
                pos=_first(element, "sl") or None,
            ))
        # Free the article. Without this the "streaming" parser holds the whole
        # document anyway, which is the classic way `iterparse` gives none of
        # the benefit it was chosen for.
        element.clear()
    return entries


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

    rows = [
        (e.lemma, e.definition, SEP.join(e.examples))
        for e in entries if e.definition or e.examples
    ]
    stats = {"entries": len(entries), "written": len(rows)}
    if not rows:
        return stats
    with conn:
        conn.executemany(
            "INSERT INTO psv_gloss (lemma, definition, examples)"
            " VALUES (?,?,?)"
            " ON CONFLICT(lemma) DO UPDATE SET"
            "   definition = excluded.definition,"
            "   examples = excluded.examples",
            rows,
        )
    stats["with_examples"] = sum(1 for e in entries if e.examples)
    return stats


@dataclass(frozen=True)
class Gloss:
    """What PSV knows about one word."""

    definition: str | None
    examples: tuple[str, ...]


def lookup(conn: sqlite3.Connection, lemma: str) -> Gloss | None:
    """EKI's learner-level entry for one word, or None.

    Absence is the common case and not an error: PSV covers about six thousand
    words and the app knows 160 316. A deployment that never imported the file
    has no table at all, and that is also None rather than a failure.
    """
    try:
        row = conn.execute(
            "SELECT definition, examples FROM psv_gloss WHERE lemma = ?",
            (lemma,),
        ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    return Gloss(
        definition=row["definition"],
        examples=tuple(e for e in (row["examples"] or "").split(SEP) if e),
    )


def imported(conn: sqlite3.Connection) -> int:
    """How many words carry a learner-level definition. Zero is a valid answer."""
    try:
        return conn.execute("SELECT COUNT(*) FROM psv_gloss").fetchone()[0]
    except sqlite3.Error:
        return 0
