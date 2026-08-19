"""The reading library is optional, and "optional" has to mean it in production.

The harvested corpus is deliberately not in the image: ERR transcripts are
© ERR and Selges keeles carries no reuse grant, so shipping them inside a
distributable image would be redistribution. Every document in this repo
therefore promises the same thing -- without `content.db` the reading library is
simply empty and everything else works.

On Cloud Run that promise broke. `EESTI_CONTENT_DB` pointed inside a directory
supplied by a `VOLUME` declaration, Cloud Run ignores `VOLUME`, and SQLite
cannot create a database in a directory that does not exist. `/api/library` and
`/api/status` both returned 500 on the live deployment while the whole suite was
green, because every test had a writable path.

That is the gap these tests close: the failure needs a database path that cannot
be created, which no test had ever asked for.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx", reason="TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402
from eesti import config  # noqa: E402


@pytest.fixture
def no_corpus(tmp_path, monkeypatch):
    """A content path that cannot be created.

    A merely *absent* directory is not the right stand-in: the fix creates
    missing parents, which is what repairs the Cloud Run case, and a test
    running as root would have that succeed and prove nothing. So the parent
    here is a regular file -- `mkdir` on it raises whatever the operating system
    raises, from any user, on any machine.
    """
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("")
    monkeypatch.setattr(config, "CONTENT_DB", str(blocker / "content.db"))
    monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(app_module, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(app_module, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


class TestLibraryDegradesRatherThanFails:
    def test_the_library_is_empty_not_broken(self, no_corpus):
        response = no_corpus.get("/api/library")
        assert response.status_code == 200, response.text
        assert response.json()["items"] == []

    def test_the_status_page_still_renders(self, no_corpus):
        """It reports on five sections; only one of them needs the corpus."""
        response = no_corpus.get("/api/status")
        assert response.status_code == 200, response.text
        assert response.json()["sections"]

    def test_health_says_the_library_is_absent(self, no_corpus):
        """Empty-because-unharvested must be distinguishable from broken."""
        assert no_corpus.get("/api/health").json()["library"] is False


class TestAvailable:
    def test_a_missing_file_is_not_available(self, tmp_path):
        from eesti.sources import available

        assert available(tmp_path / "nope.db") is False

    def test_connect_creates_a_missing_parent_directory(self, tmp_path):
        """The actual Cloud Run repair: `data/content/` does not exist there."""
        from eesti.sources import connect

        path = tmp_path / "made" / "up" / "content.db"
        connect(path).close()
        assert path.exists()

    def test_an_empty_file_is_not_available(self, tmp_path):
        """A zero-byte file is what a failed download leaves behind."""
        from eesti.sources import available

        (tmp_path / "empty.db").write_bytes(b"")
        assert available(tmp_path / "empty.db") is False

    def test_a_schema_only_database_is_not_available(self, tmp_path):
        """The one that matters. `connect` creates the database with its schema
        on the very first request, so "the file exists and is non-empty" is true
        of a deployment that has never been harvested -- which is exactly what
        the first version of this reported, and exactly the mistake the snapshot
        restore made before it."""
        from eesti.sources import available, connect

        path = tmp_path / "content.db"
        connect(path).close()
        assert available(path) is False

    def test_a_library_with_items_is_available(self, tmp_path):
        from eesti.sources import Item, add_items, available, connect, register

        path = tmp_path / "content.db"
        conn = connect(path)
        register(conn)
        source = conn.execute("SELECT id FROM sources LIMIT 1").fetchone()["id"]
        add_items(conn, [Item(
            source_id=source, skill="lugemine", level="B1",
            title="Proov", body="Ma lugesin raamatu läbi.",
        )])
        conn.close()
        assert available(path) is True
