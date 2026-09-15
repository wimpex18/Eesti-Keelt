"""Every learner database travels with the state snapshot.

Cloud Run's disk is ephemeral, so a database outside the snapshot is emptied on
the first cold start. This walks every database path in `config` and requires
each to be snapshotted or excluded with a reason.
"""

from __future__ import annotations

import pathlib

import pytest

from eesti import app as app_module
from eesti import config as config_db
from eesti.api import state as state_module

#: Databases that must NOT travel, with the reason. Anything else is a bug.
EXCLUDED = {
    # Derived from the public word list and baked into the image; ~46 MB of
    # copying something every container already has.
    "DB_PATH",
    # The harvested corpus is pushed and archived separately.
    "CONTENT_DB",
}


def _declared_databases() -> dict[str, str]:
    """`{constant name: path}` for every database path declared in `config`."""
    from eesti import config

    return {
        name: str(value)
        for name, value in vars(config).items()
        if name.endswith("_DB") and isinstance(value, (str, pathlib.Path))
    }


def test_every_declared_database_is_snapshotted_or_excluded():
    snapshotted = {str(p) for p in state_module._state_paths().values()}
    for name, path in _declared_databases().items():
        if name in EXCLUDED:
            continue
        assert path in snapshotted, (
            f"{name} = {path!r} is neither snapshotted nor listed in EXCLUDED. "
            f"On Cloud Run that means it is deleted on the next cold start."
        )


def test_the_notion_queue_is_one_of_them():
    """The Notion queue travels too."""
    assert str(config_db.NOTION_DB) in {
        str(p) for p in state_module._state_paths().values()
    }


def test_every_snapshotted_database_knows_its_learner_table():
    """Every snapshotted database names the table that means "learner data", or the
    restore guard would raise mid-restore.
    """
    assert set(state_module._state_paths()) == set(state_module.LEARNER_ROWS)


@pytest.mark.parametrize("name,table", sorted(state_module.LEARNER_ROWS.items()))
def test_each_learner_table_exists_in_its_schema(name, table, tmp_path):
    """That table exists in the database's schema."""

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


class TestWordMeaningsTravelToo:
    """A gloss stored in `vocab.db` survives the container being replaced."""

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        monkeypatch.setenv("STATE_TOKEN", "test-token")
        # Redirect on `config`, the single place the app reads these paths from.
        from eesti import config as config_module

        for name in ("PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB"):
            target = str(tmp_path / f"{name.split('_')[0].lower()}.db")
            monkeypatch.setattr(config_module, name, target)
        return TestClient(app_module.app)

    @staticmethod
    def _save_one():
        from eesti import gloss
        from eesti.providers import sonapi

        conn = gloss.connect(config_db.VOCAB_DB)
        # A word the shipped glossary does not carry, so only a real restore can supply
        # its translation.
        gloss.save(conn, "seinamaaling", sonapi.WordInfo(
            word="seinamaaling", rection=None,
            inflection_type="2", definition=None, examples=(),
            translations={"ru": ("настенная роспись",)}))
        return conn

    def test_a_gloss_survives_the_container_being_replaced(self, client):
        import pathlib

        from eesti import gloss

        self._save_one()
        head = {"x-state-token": "test-token"}
        snapshot = client.get("/api/state/export", headers=head)
        assert snapshot.status_code == 200
        assert "vocab" in snapshot.json()["databases"]

        # Simulate scale-to-zero: delete the learner databases (redirected via `config`).
        for name in ("PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB"):
            path = pathlib.Path(getattr(config_db, name))
            if path.exists():
                path.unlink()
        # The wipe is proved by the *saved* word being gone, not by a total of
        # zero: reopening the store reloads the shipped glossary, which is
        # correct and would make a count assertion fail for the wrong reason.
        assert gloss.stored(
            gloss.connect(config_db.VOCAB_DB), "seinamaaling") is None

        restored = client.post("/api/state/import", headers=head,
                               json=snapshot.json())
        assert restored.status_code == 200
        kept = gloss.stored(gloss.connect(config_db.VOCAB_DB), "seinamaaling")
        assert kept is not None and kept.russian == ("настенная роспись",)

    def test_the_daily_budget_survives_too(self, client):
        """Otherwise a restart hands back a fresh allowance, and the cap that
        makes "never batch them" arithmetic rather than a promise stops being
        one."""
        import pathlib

        from eesti import gloss

        conn = self._save_one()
        gloss._spend(conn)
        spent = gloss.spent_today(conn)
        assert spent >= 1

        head = {"x-state-token": "test-token"}
        snapshot = client.get("/api/state/export", headers=head)
        pathlib.Path(config_db.VOCAB_DB).unlink()
        client.post("/api/state/import", headers=head, json=snapshot.json())
        assert gloss.spent_today(gloss.connect(config_db.VOCAB_DB)) == spent


class TestOnePlaceDecidesWhereTheDatabasesAre:
    """The snapshot and the database helpers resolve the same files from `config`."""

    def test_the_snapshot_follows_a_redirect_of_config_alone(self, tmp_path,
                                                             monkeypatch):
        from eesti import config as config_module

        for name, stem in (("PROGRESS_DB", "p"), ("REVIEW_DB", "r"),
                           ("VOCAB_DB", "v"), ("NOTION_DB", "n")):
            monkeypatch.setattr(config_module, name, str(tmp_path / f"{stem}.db"))

        paths = state_module._state_paths()
        assert set(paths) == {"progress", "review", "vocab", "notion"}
        for path in paths.values():
            assert path.parent == tmp_path, f"{path} ignored the redirect"

    def test_the_database_helpers_follow_the_same_redirect(self, tmp_path,
                                                           monkeypatch):
        """The other half. If these read a different source from the snapshot,
        a restore lands in a file nothing reads."""
        from eesti import app as app_module
        from eesti import config as config_module

        for name, stem in (("PROGRESS_DB", "p"), ("REVIEW_DB", "r"),
                           ("VOCAB_DB", "v")):
            monkeypatch.setattr(config_module, name, str(tmp_path / f"{stem}.db"))

        opened = []
        for helper in (app_module.progress_db, app_module.review_db,
                       app_module.vocab_db, app_module.gloss_db):
            conn = helper()
            row = conn.execute("PRAGMA database_list").fetchone()
            opened.append(pathlib.Path(row[2]).parent)
        assert set(opened) == {tmp_path}, opened

    def test_importing_the_app_opens_no_database(self):
        """Importing the app opens no database."""
        import importlib
        import sqlite3

        opened = []
        real = sqlite3.connect

        def watched(target, *args, **kwargs):
            opened.append(str(target))
            return real(target, *args, **kwargs)

        sqlite3.connect = watched
        try:
            importlib.reload(importlib.import_module("eesti.app"))
        finally:
            sqlite3.connect = real
        assert not opened, f"import opened databases: {opened}"


def test_the_app_does_not_declare_its_own_copy_of_a_database_path():
    """The app declares no copy of a database path."""
    from eesti import app as app_mod

    copies = sorted(name for name, value in vars(app_mod).items()
                    if name.endswith("_DB") and isinstance(value, (str, pathlib.Path)))
    assert not copies, (
        f"`eesti.app` declares {copies}; `eesti.config` is where these live, "
        f"and `api/deps.py` reads them when it opens the file")
