"""EVKK — the Estonian Interlanguage Corpus, as a second opinion on priorities.

The learner's own error log is the first weight; EVKK (Tallinn University)
shows whether an error is hard for learners in general. Its corpus-wide error
mark counts are a public, server-rendered page.

Fetched: the taxonomy and its counts, one cached page. **Not fetched:** the
learner texts — the search is heavy on a research server and the texts carry no
reuse grant.

Among the tags, word order and verb rection are the largest annotated classes
after vocabulary; object case is small. Counts are annotation frequencies (a
parent category often absorbs marks), so read the ordering, not the numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TAXONOMY_URL = "https://evkk.tlu.ee/vers1/Marks/global_marks/marks_public.html"
TIMEOUT = 60.0

#: Five retries (backoff 1+2+4+8 s): the host is slow and intermittently answers
#: 500, and this is one request for a page that never changes.
RETRIES = 5
UA = "Eesti-Keelt/0.1 (personal language-learning tool)"

# Name, then count, with nesting carried in the URL path. Matching on the path
# rather than the CSS indent means a restyle cannot silently flatten the tree.
_ROW_RE = re.compile(
    r'<a href="[^"]*?/global_marks/((?:global_\d+/)+)markdown\.html"[^>]*>'
    r"(.*?)</a>\s*<span>(\d+)</span>",
    re.S,
)
from .clean import text as _clean_markup


@dataclass(frozen=True)
class Mark:
    """One node of the error taxonomy, with how often it was applied."""

    path: tuple[str, ...]   # ancestry, root first — the tree, made explicit
    name: str
    count: int

    @property
    def depth(self) -> int:
        return len(self.path)

    @property
    def key(self) -> str:
        return "/".join(self.path)


def parse(page: str) -> list[Mark]:
    marks: list[Mark] = []
    for m in _ROW_RE.finditer(page):
        path = tuple(p for p in m.group(1).split("/") if p)
        # Replace tags with a space so adjacent paragraphs do not merge into one word.
        name = _clean_markup(m.group(2))
        name = re.sub(r"\s+", " ", name).strip()
        # A handful of nodes carry no label and render their own id. They are
        # empty placeholders; keeping them would put ids in a report of names.
        if not name or name.startswith("global_"):
            continue
        marks.append(Mark(path, name, int(m.group(3))))
    return marks


def fetch(cache: Path | None = None) -> list[Mark]:
    """One request, cached. The taxonomy is a published standard, not a feed."""
    from .. import net

    if cache is not None and cache.exists():
        return parse(cache.read_text(encoding="utf-8"))

    page = net.get(TAXONOMY_URL, "EVKK taxonomy", timeout=TIMEOUT,
                   retries=RETRIES, ua=UA)

    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(page, encoding="utf-8")
    return parse(page)


def subtree_totals(marks: list[Mark]) -> dict[str, int]:
    """Count on a node plus everything under it, keyed by path."""
    totals: dict[str, int] = {}
    for mark in marks:
        for i in range(mark.depth):
            key = "/".join(mark.path[: i + 1])
            totals[key] = totals.get(key, 0) + mark.count
    return totals


# Our nine error tags in EVKK's vocabulary: taxonomy node names whose subtrees
# count toward each tag (except nodes in LEAF_ONLY). Every string appears verbatim
# on the EVKK page; `unmapped()` reports what is not claimed.
TAG_MAP: dict[str, tuple[str, ...]] = {
    "obj-case": (
        "Tegevuse piiritletus/piiritlematus",
        "Sihitise vead",
    ),
    "rektsioon": (
        "Rektsioon",
    ),
    "word-order": (
        "Sõnajärg ja lause teatestruktuur",
    ),
    "ma-da-inf": (
        "ma-infinitiivi kasutamine",
        "da-infinitiivi kasutamine",
        "ma-infinitiivi käändeliste vormide kasutamine",
        "des-vormi kasutamine",
    ),
    "gradation": (
        "Astmevaheldus",
    ),
    "loc-case": (
        "sise- ja välikohakäänete segamini ajamine",
        "latiivi, lokatiivi ja separatiivi kasutamine",
        "alalütleva käände kasutamine ajatähenduses",
    ),
    "gen-stem": (
        "põhikäänded",
    ),
    "verb-form": (
        "Ajavormide moodustamine aktiivis ja supressiivis",
        "Tegumood: umbisikulise tegumoe moodustamine",
    ),
    "vocab": (
        "Leksikaalsed",
    ),
}

# Names whose subtree would swallow children mapped to a different tag. Currently
# empty: no mapped node is an ancestor of another; `tests/test_evkk_mapping.py`
# fails if that changes without an entry here.
LEAF_ONLY: frozenset[str] = frozenset()


def _keys_for(marks: list[Mark], names: tuple[str, ...]) -> set[str]:
    return {m.key for m in marks if m.name in names}


def tag_weights(marks: list[Mark]) -> dict[str, int]:
    """How many annotated learner errors fall under each of our nine tags."""
    totals = subtree_totals(marks)
    weights: dict[str, int] = {}
    for tag, names in TAG_MAP.items():
        roots = _keys_for(marks, names)
        # Drop any root contained in another, so a nested pair is not counted twice.
        roots = {r for r in roots if not any(r != o and r.startswith(o + "/") for o in roots)}
        weights[tag] = sum(
            (next(m.count for m in marks if m.key == r) if r in LEAF_ONLY else totals[r])
            for r in roots
        )
    return weights


def unmapped(marks: list[Mark]) -> int:
    """Marks no tag of ours claims — the honest denominator for any percentage."""
    claimed: set[str] = set()
    for names in TAG_MAP.values():
        for root in _keys_for(marks, names):
            claimed |= {m.key for m in marks if m.key == root or m.key.startswith(root + "/")}
    return sum(m.count for m in marks if m.key not in claimed)


SCHEMA = """
CREATE TABLE IF NOT EXISTS evkk_marks (
    path   TEXT PRIMARY KEY,
    parent TEXT,
    name   TEXT NOT NULL,
    depth  INTEGER NOT NULL,
    count  INTEGER NOT NULL,
    tag    TEXT             -- our error tag, NULL where the taxonomy is finer
);
CREATE INDEX IF NOT EXISTS idx_evkk_tag ON evkk_marks(tag);
"""


def store(conn, marks: list[Mark]) -> int:
    """Persist the taxonomy so curriculum weighting needs no network."""
    conn.executescript(SCHEMA)
    owner: dict[str, str] = {}
    for tag, names in TAG_MAP.items():
        for root in _keys_for(marks, names):
            for m in marks:
                if m.key == root or m.key.startswith(root + "/"):
                    owner[m.key] = tag
    with conn:
        conn.execute("DELETE FROM evkk_marks")
        conn.executemany(
            "INSERT INTO evkk_marks (path,parent,name,depth,count,tag)"
            " VALUES (?,?,?,?,?,?)",
            [
                (m.key, "/".join(m.path[:-1]) or None, m.name, m.depth,
                 m.count, owner.get(m.key))
                for m in marks
            ],
        )
    return len(marks)
