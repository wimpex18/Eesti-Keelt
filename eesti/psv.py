"""*Eesti keele põhisõnavara sõnastik* — definitions written for learners.

Sõnaveeb's definitions are written for native speakers; PSV (EKI, 2014,
CC BY 4.0) restates about 6 000 basic words simply, with examples. The file is
committed in `deploy/eki/` and imported at image build.

**Stored in the words database (`eesti.db`), not `vocab.db`.** It is reference
data, the same for everyone; `vocab.db` is learner state that a snapshot
restore replaces.

**Its own table.** `psv_gloss.definition` (learner-level) and
`word_gloss.definition` (the live dictionary's) are different claims for
different audiences; the card reads both and prefers PSV.

**Format:** per `schema_psv.xsd` — `A` article, `P/mg/m` headword, `S/tp/grg/sl`
part of speech, `S/tp/tg/dg/d` definition, `S/tp/tg/ng/n` example. EKI's XML
does not validate against its schema, so fields are read by descendant tag and
all but the headword are optional.
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
    """Read the dictionary via `ekixml.articles` (no root, undeclared `c:` prefixes,
    one article per line). Articles without a headword are skipped.
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


#: `rliik` kinds shown as a word's rektsioon: object (`obj`), case frame (`kn`),
#: infinitive (`inf`), postposition phrase (`ks`), adverbial question (`yld`,
#: `kust`). Clause (`kla`) and subject frames are left out.
RECTION_KINDS = ("obj", "kn", "inf", "ks", "yld")


def _rection(article) -> tuple[str, ...]:
    found = [ekixml.text(r) for r in article.iter("rek") if r.get("rliik") in RECTION_KINDS]
    return tuple(dict.fromkeys(f for f in found if f))


def _one_per_lemma(entries: list[Entry]) -> list[Entry]:
    """The article to show when EKI has several for a lemma (homonyms such as `arm`):
    the most common by EKI's `sag` tier, then EKI's homonym numbering.
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
    """Write the learner-level definitions into the words database. Idempotent."""
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
        # The file is the whole truth: lemmas it no longer has are removed.
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
    """EKI's learner-level entry for one word, or None (the common case, including
    when the file was never imported).
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
