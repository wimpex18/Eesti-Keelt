"""Every learner database must travel with the snapshot.

Cloud Run's disk is ephemeral and the service scales to zero, so anything not
in the snapshot is deleted the first time the learner takes a break. The
snapshot is not a backup; it is the only reason state exists at all.

`notion.db` was missed. Queued corrections — the ones waiting for a person to
review before they go to the Notion log — were dropped on every cold start, so
a queue whose entire purpose is to hold things until someone looks at them held
nothing across fifteen idle minutes. Nothing failed, nothing logged, the list
was just empty again.

That is the shape of the failure worth guarding: adding a database is easy and
remembering to add it here is not, and forgetting is silent. So this test walks
the app's own module-level database paths and demands each one is either
snapshotted or listed as deliberately excluded.
"""

from __future__ import annotations

import pytest

from eesti import app as app_module

#: Databases that must NOT travel, with the reason. Anything else is a bug.
EXCLUDED = {
    # Derived from the public word list and baked into the image; ~46 MB of
    # copying something every container already has.
    "DB_PATH",
    # The harvested corpus. It has its own path -- pushed once, archived by the
    # Worker -- because it is far larger and never changes as the learner works.
    "CONTENT_DB",
}


def _declared_databases() -> dict[str, str]:
    """`{constant name: path}` for every database path the app declares."""
    return {
        name: value
        for name, value in vars(app_module).items()
        if name.endswith("_DB") and isinstance(value, str)
    }


def test_every_declared_database_is_snapshotted_or_excluded():
    snapshotted = {str(p) for p in app_module._state_paths().values()}
    for name, path in _declared_databases().items():
        if name in EXCLUDED:
            continue
        assert path in snapshotted, (
            f"{name} = {path!r} is neither snapshotted nor listed in EXCLUDED. "
            f"On Cloud Run that means it is deleted on the next cold start."
        )


def test_the_notion_queue_is_one_of_them():
    """Named explicitly, because it is the one that was missed."""
    assert str(app_module.NOTION_DB) in {
        str(p) for p in app_module._state_paths().values()
    }


def test_every_snapshotted_database_knows_its_learner_table():
    """The restore guard reads a table per database to decide whether there is
    real work to protect. A database in the snapshot with no entry here would
    raise a KeyError mid-restore -- losing the snapshot it was restoring."""
    assert set(app_module._state_paths()) == set(app_module.LEARNER_ROWS)


@pytest.mark.parametrize("name,table", sorted(app_module.LEARNER_ROWS.items()))
def test_each_learner_table_exists_in_its_schema(name, table, tmp_path):
    """A renamed table would make `_has_learner_data` return True forever --
    the failure mode that once made every restore silently refuse."""
    import sqlite3

    connectors = {
        "progress": ("eesti.progress", "connect"),
        "review": ("eesti.review", "connect"),
        "vocab": ("eesti.vocab", "connect"),
        "notion": ("eesti.notion", "connect"),
    }
    module_name, func = connectors[name]
    module = __import__(module_name, fromlist=[func])
    conn = getattr(module, func)(tmp_path / f"{name}.db")
    found = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    assert found, f"{name}: no table {table!r}"
    conn.close()
