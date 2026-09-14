"""The EVKK tag map, checked without redistributing EVKK.

| Check | Needs |
|---|---|
| the unmapped remainder stays in the denominator | arithmetic over any taxonomy |
| no mapped subtree swallows a differently-tagged node | `TAG_MAP` + `LEAF_ONLY` + a tree shape |
| every mapped name is really on the page | the live page |

The first two run here against a taxonomy written for the test (real `TAG_MAP`
names, invented structure and counts). EVKK's page carries no reuse licence and
its host is unreliable, so it is neither committed nor fetched in CI; `cli evkk`
checks the third on live data, and this file checks it against a cached copy
when one exists.
"""

from __future__ import annotations

import pytest

from eesti.config import CACHE, TAGS
from eesti.harvest import evkk

CACHED = CACHE / "evkk_marks.html"


def _mark(path: tuple[str, ...], name: str, count: int) -> evkk.Mark:
    return evkk.Mark(path=path, name=name, count=count)


@pytest.fixture(scope="module")
def marks() -> list[evkk.Mark]:
    """The real taxonomy, when a cached copy happens to be on this machine."""
    if not CACHED.exists():
        pytest.skip("no cached taxonomy")
    return evkk.parse(CACHED.read_text(encoding="utf-8"))


@pytest.fixture
def taxonomy() -> list[evkk.Mark]:
    """A taxonomy of this project's own making, shaped like EVKK's (names from
    `TAG_MAP`, invented tree and counts).
    """
    marks = []
    for n, (tag, names) in enumerate(evkk.TAG_MAP.items()):
        root = f"global_{n}"
        for m, name in enumerate(names):
            key = (root, f"global_{n}_{m}")
            marks.append(_mark(key, name, 100 + m))
            # A child, so subtree arithmetic has something to add up.
            marks.append(_mark(key + (f"global_{n}_{m}_leaf",), f"{name} alam", 7))
    # Something no tag claims, so the remainder is never zero.
    marks.append(_mark(("global_x",), "Miski muu", 555))
    return marks


#: EVKK-shaped page markup written for the test (a `margin-left` div, an anchor
#: whose href carries `global_N/` ancestry, a count `<span>`), so `parse()` is
#: covered without copying their data.
MARKUP = """
<div style="margin-left:20px">
        <a href="https://evkk.tlu.ee/vers1/Marks/global_marks/global_100/markdown.html"
           style="">Leksikaalsed</a>
            <span>352</span>
</div>
<div style="margin-left:40px">
        <a href="https://evkk.tlu.ee/vers1/Marks/global_marks/global_100/global_101/markdown.html"
           style=""><p>Sobimatu</p><p>sõnavalik</p></a>
            <span>41</span>
</div>
<div style="margin-left:40px">
        <a href="https://evkk.tlu.ee/vers1/Marks/global_marks/global_100/global_102/markdown.html"
           style="">global_102</a>
            <span>0</span>
</div>
<div style="margin-left:20px">
        <a href="https://evkk.tlu.ee/vers1/Marks/global_marks/global_200/markdown.html"
           style="">Rektsioon</a>
            <span>5170</span>
</div>
"""


class TestReadingTheirMarkup:
    """`parse()` against the page shape, which nothing exercised before."""

    def test_it_finds_every_labelled_node(self):
        assert [m.name for m in evkk.parse(MARKUP)] == [
            "Leksikaalsed", "Sobimatu sõnavalik", "Rektsioon"]

    def test_the_count_comes_off_the_span(self):
        assert {m.name: m.count for m in evkk.parse(MARKUP)}["Rektsioon"] == 5170

    def test_ancestry_comes_from_the_url_not_the_indentation(self):
        """Matching on the href rather than the CSS indent is deliberate: a
        restyle cannot silently flatten the tree."""
        by_name = {m.name: m for m in evkk.parse(MARKUP)}
        assert by_name["Leksikaalsed"].depth == 1
        assert by_name["Sobimatu sõnavalik"].depth == 2
        assert by_name["Sobimatu sõnavalik"].key.startswith(
            by_name["Leksikaalsed"].key + "/")

    def test_markup_inside_a_label_is_joined_with_a_space(self):
        """Tags become spaces, so adjacent paragraphs do not merge into one word."""
        assert "Sobimatu sõnavalik" in {m.name for m in evkk.parse(MARKUP)}

    def test_a_node_labelled_with_its_own_id_is_dropped(self):
        """A handful render their id instead of a name. Keeping them would put
        ids in a report of names."""
        assert not [m for m in evkk.parse(MARKUP) if m.name.startswith("global_")]

    def test_a_page_that_stopped_matching_returns_nothing_rather_than_guessing(self):
        """`cmd_evkk` turns this into "the page shape may have changed" and
        writes nothing, which is the honest response to a restyle."""
        assert evkk.parse("<html><body>midagi muud</body></html>") == []

    def test_subtree_totals_add_a_node_to_its_ancestors(self):
        totals = evkk.subtree_totals(evkk.parse(MARKUP))
        parent = next(m for m in evkk.parse(MARKUP) if m.name == "Leksikaalsed")
        assert totals[parent.key] == 352 + 41


class TestTheInvariantsOfOurOwnCode:
    """These run everywhere. No third-party data, no network, no cache."""

    def test_the_unmapped_remainder_is_counted_not_dropped(self, taxonomy):
        """Weights are a share of all annotated errors, including the unmapped remainder."""
        total = sum(m.count for m in taxonomy)
        assert sum(evkk.tag_weights(taxonomy).values()) + evkk.unmapped(taxonomy) == total

    def test_nothing_a_tag_claims_is_left_out_of_its_weight(self, taxonomy):
        """A mapped node contributes its whole subtree, so the child invented
        above has to show up in its parent's tag."""
        weights = evkk.tag_weights(taxonomy)
        assert all(w > 0 for w in weights.values()), weights
        assert set(weights) == set(evkk.TAG_MAP)

    def test_no_mapped_subtree_swallows_a_differently_tagged_node(self, taxonomy):
        """No mapped node is an ancestor of a differently-tagged mapped node unless listed
        in `LEAF_ONLY`.
        """
        keys: dict[str, list[str]] = {}
        for mark in taxonomy:
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
            for outer in mapped for inner in mapped
            if inner != outer and inner.startswith(outer + "/")
            and mapped[inner] != mapped[outer]
        ]
        assert not overlaps, f"double-counted {overlaps} — list the outer in LEAF_ONLY"

    def test_every_tag_it_weights_is_one_the_error_log_uses(self):
        """`TAG_MAP`'s keys are exactly the Notion log's tags."""
        assert set(evkk.TAG_MAP) <= set(TAGS)

    def test_a_name_that_matches_nothing_weighs_zero(self, taxonomy):
        """The failure mode the live check exists for, reproduced offline: a
        renamed or mistyped category does not raise, it silently contributes
        nothing and quietly moves the topic order."""
        weights = evkk.tag_weights(
            [m for m in taxonomy if m.name not in evkk.TAG_MAP["rektsioon"]])
        assert weights["rektsioon"] == 0


@pytest.mark.skipif(
    not CACHED.exists(),
    reason=f"no cached taxonomy at {CACHED} — `cli evkk` writes one, and "
           "refuses on a zero-weight tag, which is where this is really checked",
)
class TestAgainstTheRealPage:
    """Only when a cached copy happens to exist. Never committed, never fetched
    by CI — see the module docstring."""

    def test_every_mapped_name_really_is_on_the_page(self, marks):
        names = {m.name for m in marks}
        missing = {
            (tag, name)
            for tag, wanted in evkk.TAG_MAP.items()
            for name in wanted
            if name not in names
        }
        assert not missing, f"TAG_MAP names absent from the taxonomy: {sorted(missing)}"

    def test_no_tag_weighs_zero_against_real_data(self, marks):
        weights = evkk.tag_weights(marks)
        assert not [t for t, n in weights.items() if n == 0], weights
