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

import pathlib

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


class TestWordMeaningsTravelToo:
    """`gloss.py` says its store "lives in `vocab.db`, which the state snapshot
    carries". That is the whole reason the table is there rather than in a file
    of its own — a gloss store outside the snapshot would be emptied on every
    cold start, and the module exists because `sonapi`'s disk cache already
    was. A claim like that is a fact about the code, so it gets a test.
    """

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        monkeypatch.setenv("STATE_TOKEN", "test-token")
        # Redirected on `config`, which is now the single place the app reads
        # these from. It used to be patched on `app` instead, because `app`
        # kept its own copies bound at import -- and that split is exactly the
        # bug that was fixed: `_state_paths()` read one set and the database
        # helpers the other, so a restore could land in a different file from
        # the one the app then opened.
        from eesti import config as config_module

        for name in ("PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB"):
            target = str(tmp_path / f"{name.split('_')[0].lower()}.db")
            monkeypatch.setattr(config_module, name, target)
            monkeypatch.setattr(app_module, name, target, raising=False)
        return TestClient(app_module.app)

    @staticmethod
    def _save_one():
        from eesti import gloss
        from eesti.providers import sonapi

        conn = gloss.connect(app_module.VOCAB_DB)
        gloss.save(conn, "kleit", sonapi.WordInfo(
            word="kleit", word_classes=(), rection=None, inflection_type="2",
            definition=None, examples=(), translations={"ru": ("платье",)}))
        return conn

    def test_a_gloss_survives_the_container_being_replaced(self, client):
        import pathlib

        from eesti import gloss

        self._save_one()
        head = {"x-state-token": "test-token"}
        snapshot = client.get("/api/state/export", headers=head)
        assert snapshot.status_code == 200
        assert "vocab" in snapshot.json()["databases"]

        # What Cloud Run does when it scales to zero.
        for name in ("PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB"):
            path = pathlib.Path(getattr(app_module, name))
            if path.exists():
                path.unlink()
        assert gloss.stats(gloss.connect(app_module.VOCAB_DB))["words"] == 0

        restored = client.post("/api/state/import", headers=head,
                               json=snapshot.json())
        assert restored.status_code == 200
        kept = gloss.stored(gloss.connect(app_module.VOCAB_DB), "kleit")
        assert kept is not None and kept.russian == ("платье",)

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
        pathlib.Path(app_module.VOCAB_DB).unlink()
        client.post("/api/state/import", headers=head, json=snapshot.json())
        assert gloss.spent_today(gloss.connect(app_module.VOCAB_DB)) == spent


class TestOnePlaceDecidesWhereTheDatabasesAre:
    """`app.py` used to keep its own copies of the four learner paths, bound at
    import from `config`.

    Two names for one file is a fork waiting to happen, and it forked: the
    database helpers read `app`'s copies while `_state_paths()` — the snapshot
    — read the same names, so redirecting one without the other pointed the
    restore at a different file from the one the app then opened. Nothing
    failed in production, because nothing redirects them there; it failed in
    tests, silently, by writing somewhere real.

    Both now resolve `config` when called. These tests exist so the next reader
    who adds a fifth database is told where it belongs.
    """

    def test_the_snapshot_follows_a_redirect_of_config_alone(self, tmp_path,
                                                             monkeypatch):
        from eesti import app as app_module
        from eesti import config as config_module

        for name, stem in (("PROGRESS_DB", "p"), ("REVIEW_DB", "r"),
                           ("VOCAB_DB", "v"), ("NOTION_DB", "n")):
            monkeypatch.setattr(config_module, name, str(tmp_path / f"{stem}.db"))

        paths = app_module._state_paths()
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
        """The breaker used to bind at import, which resolved `progress.db`
        before anything could redirect it — the anti-pattern this project has
        a written habit about, and one the test suite had to work around."""
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
