"""EVKK — the Estonian Interlanguage Corpus, as a second opinion on priorities.

Every drill in this app is weighted by **one** learner's error log. That log is
real and it is the right thing to optimise for, but it cannot answer a question
it is too small to see: *is object case actually hard for learners of Estonian,
or is it just hard for me?*

Tallinn University's Eesti vahekeele korpus is where that question gets an
answer. It is a corpus of texts written by learners of Estonian, annotated by
linguists against a published error taxonomy, and its **corpus-wide mark counts
are served as a public page** — no login, no API key, server-rendered HTML.
51 467 annotated errors, which is four orders of magnitude more evidence than a
personal log.

## What is fetched, and what is deliberately not

Fetched: **the taxonomy and its counts** — 202 category names and how often each
was applied. That is one small page, requested once and cached.

Not fetched: **the learner texts themselves.** The corpus search works (POST to
`Search/search_results.html`, plain form encoding, no JS) and would hand back
authentic wrong sentences — the most tempting material in this whole project.
Two reasons it stays untouched. A single-word query returned **6 MB**, and this
is a research server with no rate limiting to protect it; and the site carries no
explicit reuse grant, so the texts are other people's writing with no permission
attached. The counts are facts about a published taxonomy. The texts are not.

So this module answers "what should the curriculum weight?" and stops there.

## What it found

Counted strictly, object-case marks are **~1.3 %** of all annotated errors. The
two largest categories are **verb rection (4 450)** and **word order (5 889)** —
one of which this app had a tag for and no drills, and the other of which it
barely modelled at all. That does not demote the personal log: the log is
evidence about *this* learner and stays the first weight. It does say the
curriculum should not assume one person's ranking generalises, and it makes the
rection data that `providers/sonapi.py` returns considerably more valuable than
it looked when it was wired.

Counts are **annotation** frequencies, not incidence rates. They reflect what
annotators chose to mark and what the sub-corpora contain (exam essays are
heavily represented), and a parent category is often marked where a specific
child would have done — `põhikäänded` carries 1 331 marks of its own. Read the
ordering, not the absolute numbers.
"""

from __future__ import annotations

import html as _html
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

TAXONOMY_URL = "https://evkk.tlu.ee/vers1/Marks/global_marks/marks_public.html"
TIMEOUT = 60.0
RETRIES = 3
UA = "Eesti-Keelt/0.1 (personal language-learning tool)"

# Name, then count, with nesting carried in the URL path. Matching on the path
# rather than the CSS indent means a restyle cannot silently flatten the tree.
_ROW_RE = re.compile(
    r'<a href="[^"]*?/global_marks/((?:global_\d+/)+)markdown\.html"[^>]*>'
    r"(.*?)</a>\s*<span>(\d+)</span>",
    re.S,
)
_TAG_RE = re.compile(r"<[^>]+>")


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
        name = _html.unescape(_TAG_RE.sub("", m.group(2)))
        name = re.sub(r"\s+", " ", name).strip()
        # A handful of nodes carry no label and render their own id. They are
        # empty placeholders; keeping them would put ids in a report of names.
        if not name or name.startswith("global_"):
            continue
        marks.append(Mark(path, name, int(m.group(3))))
    return marks


def fetch(cache: Path | None = None) -> list[Mark]:
    """One request, cached. The taxonomy is a published standard, not a feed."""
    if cache is not None and cache.exists():
        return parse(cache.read_text(encoding="utf-8"))

    req = urllib.request.Request(TAXONOMY_URL, headers={"User-Agent": UA})
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                page = resp.read().decode("utf-8", errors="replace")
            break
        except Exception as exc:  # noqa: BLE001 - retry anything, then give up
            last = exc
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"EVKK taxonomy unreachable: {last}")

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


# Our nine error tags, expressed in EVKK's vocabulary. Each entry is a list of
# taxonomy node names; a node contributes its whole subtree unless it is listed
# in LEAF_ONLY, which exists because two of these names sit above children that
# belong to a different tag of ours.
#
# Written out by hand against the taxonomy, so it is auditable: every string
# below appears verbatim on the EVKK page, and `unmapped()` reports whatever
# these lines fail to claim rather than letting it vanish.
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

# `Leksikaalsed` is a top-level category whose subtree is genuinely all
# vocabulary, so it is not here. This set is for names that would otherwise
# swallow children we map elsewhere.
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
