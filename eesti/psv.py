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

## Two definitions, two columns

A PSV definition and a Sõnaveeb definition are **different claims about
different audiences**, not two guesses at one claim, so they do not share a
column — the same rule that keeps `level` and `band` apart.

`word_gloss.simple_definition` holds PSV's; `word_gloss.definition` holds
Sõnaveeb's. `save()` never overwrites the first, because the whole value of the
learner-level wording is that the native-level wording does not replace it the
first time the learner opens that card.

## A baseline, not a ceiling

A PSV row carries an Estonian definition and examples. It carries **no Russian
translation, no rection and no muuttüüp** — exactly the shape of the shipped
seed glossary, and it inherits the seed's rule: `remember()` still asks
Sõnaveeb about a PSV-filled word, because otherwise importing this file would
have quietly made the word card *worse* for the 6 000 commonest words by
filling their rows and so preventing the lookup that carries the Russian.

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


def store(conn: sqlite3.Connection, entries: list[Entry]) -> dict[str, int]:
    """Write the learner-level definitions into the gloss store.

    `INSERT ... ON CONFLICT` updating **only** the two PSV columns, which is the
    whole design in one statement: a word Sõnaveeb has already answered for
    keeps its Russian, its rection and its muuttüüp, and gains a definition
    written for a learner. A word nobody has looked up yet gets a row that
    `remember()` will still enrich, because `fetched` marks it a baseline.
    """
    from .gloss import SCHEMA

    conn.executescript(SCHEMA)
    _migrate(conn)

    rows = [
        (e.lemma, e.definition, SEP.join(e.examples), SOURCE)
        for e in entries if e.definition or e.examples
    ]
    stats = {"entries": len(entries), "written": len(rows)}
    if not rows:
        return stats
    with conn:
        conn.executemany(
            """INSERT INTO word_gloss
                 (lemma, russian, simple_definition, examples, fetched)
               VALUES (?, '', ?, ?, ?)
               ON CONFLICT(lemma) DO UPDATE SET
                 simple_definition = excluded.simple_definition,
                 examples = excluded.examples""",
            rows,
        )
    stats["with_examples"] = sum(1 for e in entries if e.examples)
    return stats


def _migrate(conn: sqlite3.Connection) -> None:
    """Add the two PSV columns to a store built before they existed.

    The same reasoning as `sources._migrate`: `vocab.db` travels in the state
    snapshot, so a learner can be carrying a store older than this module, and
    failing to open it would lose every gloss they have over one `ALTER TABLE`.
    """
    have = {r[1] for r in conn.execute("PRAGMA table_info(word_gloss)")}
    for column in ("simple_definition", "examples"):
        if column not in have:
            conn.execute(f"ALTER TABLE word_gloss ADD COLUMN {column} TEXT")


def imported(conn: sqlite3.Connection) -> int:
    """How many words carry a learner-level definition. Zero is a valid answer."""
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM word_gloss WHERE simple_definition IS NOT NULL"
        ).fetchone()[0]
    except sqlite3.Error:
        return 0
