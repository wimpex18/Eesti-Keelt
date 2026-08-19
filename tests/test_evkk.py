"""EVKK taxonomy parsing and tag weighting.

No network: the parser is exercised against a fixture shaped like the real page,
and the invariants that matter are arithmetic ones — nothing counted twice,
nothing quietly dropped.
"""

from __future__ import annotations

import sqlite3

from eesti.harvest import evkk


def _row(ids: tuple[str, ...], name: str, count: int, indent: int) -> str:
    path = "/".join(ids)
    return (
        f'<div style="margin-left:{indent}px">'
        f'<a href="https://evkk.tlu.ee/vers1/Marks/global_marks/{path}/markdown.html"'
        f' style="">{name}</a> <span>{count}</span></div>'
    )


PAGE = "".join(
    [
        _row(("global_1",), "Leksikaalgrammatilised", 5, 20),
        _row(("global_1", "global_2"), "Tegevuse piiritletus/piiritlematus", 100, 40),
        _row(
            ("global_1", "global_2", "global_3"),
            "osastavaline, omastavaline/ nimetavaline objekt", 45, 60,
        ),
        _row(("global_4",), "Süntaktilised", 85, 20),
        _row(("global_4", "global_5"), "Sõnaühendi süntaks", 19, 40),
        _row(("global_4", "global_5", "global_6"), "Rektsioon", 43, 60),
        _row(
            ("global_4", "global_5", "global_6", "global_7"), "verbirektsioon", 4450, 80
        ),
        _row(("global_8",), "global_99887766", 0, 20),
    ]
)


def test_parse_reads_the_tree_from_the_url_not_the_indent():
    marks = evkk.parse(PAGE)
    by_name = {m.name: m for m in marks}
    rektsioon = by_name["Rektsioon"]
    assert rektsioon.depth == 3
    assert rektsioon.path[:2] == ("global_4", "global_5")


def test_unlabelled_placeholder_nodes_are_dropped():
    # A few nodes render their own id for a name. Keeping them would put
    # database ids into a report meant to be read.
    assert all(not m.name.startswith("global_") for m in evkk.parse(PAGE))


def test_subtree_totals_include_the_node_itself():
    totals = evkk.subtree_totals(evkk.parse(PAGE))
    assert totals["global_4/global_5/global_6"] == 43 + 4450
    assert totals["global_4"] == 85 + 19 + 43 + 4450


def test_every_mark_is_either_tagged_or_counted_as_unmapped():
    """The invariant that makes any percentage in the report honest."""
    marks = evkk.parse(PAGE)
    weights = evkk.tag_weights(marks)
    assert sum(weights.values()) + evkk.unmapped(marks) == sum(m.count for m in marks)


def test_nested_roots_are_not_counted_twice():
    marks = evkk.parse(PAGE)
    # obj-case names both a parent and, in the real taxonomy, categories under
    # it; the subtree must be claimed once.
    assert evkk.tag_weights(marks)["obj-case"] == 100 + 45


def test_store_records_the_owning_tag():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    marks = evkk.parse(PAGE)
    assert evkk.store(conn, marks) == len(marks)

    rows = {r["name"]: r["tag"] for r in conn.execute("SELECT name, tag FROM evkk_marks")}
    assert rows["verbirektsioon"] == "rektsioon"
    assert rows["osastavaline, omastavaline/ nimetavaline objekt"] == "obj-case"
    assert rows["Süntaktilised"] is None  # a parent we deliberately do not claim


def test_store_is_idempotent():
    conn = sqlite3.connect(":memory:")
    marks = evkk.parse(PAGE)
    evkk.store(conn, marks)
    evkk.store(conn, marks)
    assert conn.execute("SELECT COUNT(*) FROM evkk_marks").fetchone()[0] == len(marks)


def test_tag_map_only_names_tags_the_error_log_uses():
    from eesti.config import TAGS

    assert set(evkk.TAG_MAP) <= set(TAGS)
