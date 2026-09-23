"""An unavailable source must not erase the library or block another source."""

import argparse

from eesti import config
from eesti.cli.harvest import cmd_harvest_exam, cmd_harvest_reading
from eesti.harvest import eis, harno, selges
from eesti.sources import Item, add_items, clear_source, connect, register


def test_empty_reading_response_preserves_existing_corpus(tmp_path, monkeypatch):
    path = tmp_path / "content.db"
    with connect(path) as conn:
        register(conn)
        item = Item(source_id="selges-keeles", skill="lugemine", body="Tere!")
        add_items(conn, [item])
    monkeypatch.setattr(selges, "fetch", lambda **kwargs: [])
    assert cmd_harvest_reading(argparse.Namespace(db=str(path), limit=None)) == 1
    with connect(path) as conn:
        assert conn.execute("SELECT id FROM items").fetchone()[0] == item.id


def test_removing_source_also_removes_its_topic_links(tmp_path):
    with connect(tmp_path / "content.db") as conn:
        register(conn)
        first = Item(source_id="selges-keeles", skill="lugemine", title="Esimene")
        second = Item(source_id="harno", skill="lugemine", title="Teine")
        add_items(conn, [first, second])
        conn.executemany("INSERT INTO topic_items VALUES (?, ?, ?)", [
            ("gen-stem", first.id, 3), ("gen-stem", second.id, 3),
        ])
        conn.commit()
        assert clear_source(conn, first.source_id) == 1
        assert [row[0] for row in conn.execute("SELECT item_id FROM topic_items")] == [second.id]


def test_eis_outage_keeps_existing_tasks_and_harvests_harno(tmp_path, monkeypatch):
    path = tmp_path / "content.db"
    monkeypatch.setattr(config, "CONTENT_DB", path)
    with connect(path) as conn:
        register(conn)
        old = Item(source_id="eis", skill="lugemine", title="Lugemine")
        add_items(conn, [old])

    def unavailable(*args, **kwargs):
        raise TimeoutError("upstream")

    monkeypatch.setattr(eis, "catalogue", unavailable)
    monkeypatch.setattr(harno, "catalogue", lambda: [harno.Material(
        url="https://harno.ee/example.pdf", level="A2", skill="lugemine",
        title="A2 lugemine", kind="ulesanne", fmt="pdf",
    )])
    assert cmd_harvest_exam(argparse.Namespace(levels="A2", download=False)) == 0
    with connect(path) as conn:
        assert {row[0] for row in conn.execute("SELECT source_id FROM items")} == {"eis", "harno"}
        assert conn.execute("SELECT id FROM items WHERE source_id='eis'").fetchone()[0] == old.id
