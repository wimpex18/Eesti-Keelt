"""The EVKK tag map, checked against the taxonomy instead of asserted about it.

`TAG_MAP` translates this project's nine error tags into EVKK's category names,
and the curriculum weights topic order by what comes out. Two things about it
were claims rather than checks until 2026-09-11:

* that every name in it "appears verbatim on the EVKK page" — if one stopped
  appearing, its tag would silently weigh zero and the topic order would shift
  with nothing to say why;
* that `LEAF_ONLY` "exists because two of these names sit above children that
  belong to a different tag" — while being empty, so the double-counting guard
  it describes was doing nothing.

These run against a cached copy of the page when there is one and skip when
there is not, because EVKK is a research host that answered 500 on two of three
attempts the day this was written.
"""

from __future__ import annotations

import pytest

from eesti.config import CACHE
from eesti.harvest import evkk

CACHED = CACHE / "evkk_marks.html"

pytestmark = pytest.mark.skipif(
    not CACHED.exists(),
    reason="run `python -m eesti.cli evkk` once to cache the taxonomy",
)


@pytest.fixture(scope="module")
def marks():
    return evkk.parse(CACHED.read_text(encoding="utf-8"))


def test_every_mapped_name_really_is_on_the_page(marks):
    """A typo here does not raise; it makes a tag weigh nothing."""
    names = {m.name for m in marks}
    missing = {
        (tag, name)
        for tag, wanted in evkk.TAG_MAP.items()
        for name in wanted
        if name not in names
    }
    assert not missing, f"TAG_MAP names absent from the taxonomy: {sorted(missing)}"


def test_no_mapped_subtree_swallows_a_differently_tagged_node(marks):
    """What `LEAF_ONLY` is for, checked rather than commented.

    A mapped node contributes its whole subtree. If one mapped node is an
    ancestor of another carrying a different tag, the descendant's errors are
    counted under both — and the fix is to list the ancestor in `LEAF_ONLY`.
    """
    keys: dict[str, list[str]] = {}
    for mark in marks:
        keys.setdefault(mark.name, []).append(mark.key)
    mapped = {
        key: tag
        for tag, names in evkk.TAG_MAP.items()
        for name in names
        for key in keys.get(name, [])
        if name not in evkk.LEAF_ONLY
    }
    overlaps = [
        (mapped[outer], mapped[inner])
        for outer in mapped
        for inner in mapped
        if inner != outer and inner.startswith(outer + "/")
        and mapped[inner] != mapped[outer]
    ]
    assert not overlaps, (
        f"double-counted subtrees {overlaps} — list the outer name in LEAF_ONLY"
    )


def test_the_unmapped_remainder_is_counted_not_dropped(marks):
    """The weights are a share of all 51 467 errors, not of the mapped ones.

    Roughly 40 % of the corpus's annotations fall outside these nine tags. That
    share has to stay in the denominator, or every tag's percentage would be
    inflated by exactly the amount this app cannot practise.
    """
    total = sum(m.count for m in marks)
    assert sum(evkk.tag_weights(marks).values()) + evkk.unmapped(marks) == total
