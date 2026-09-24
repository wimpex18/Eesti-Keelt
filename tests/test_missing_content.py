"""The app works without its reading corpus, including when the corpus path cannot
be created.

The corpus is not in the image. On Cloud Run the content directory may not
exist (`VOLUME` is ignored), so every route must degrade to an empty library
instead of a 500.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402
from eesti import config as config_db
from eesti import config  # noqa: E402


@pytest.fixture
def no_corpus(tmp_path, monkeypatch):
    """A content path that cannot be created: its parent is a regular file, so `mkdir`
    fails for any user on any machine.
    """
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("")
    monkeypatch.setattr(config, "CONTENT_DB", str(blocker / "content.db"))
    monkeypatch.setattr(config_db, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(config_db, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(config_db, "VOCAB_DB", str(tmp_path / "v.db"))
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
        """Health says the library is absent, distinguishing empty from broken."""
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
        """A schema-only database counts as unavailable (`connect` creates the schema on
        first open).
        """
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


@pytest.fixture(params=["cannot-be-created", "no-directory", "directory-no-file"])
def corpusless(request, tmp_path, monkeypatch):
    """Every way a container meets the app without its corpus: an uncreatable path, a
    missing directory, and an existing directory with no file.

    Returns `(client, fresh)`; `fresh()` is called before every request, because
    one request's `sources.connect` creates tables that would mask the next.
    """
    counter = iter(range(10_000))

    def fresh():
        n = next(counter)
        if request.param == "cannot-be-created":
            blocker = tmp_path / f"not-a-directory-{n}"
            blocker.write_text("")
            target = blocker / "content.db"
        elif request.param == "no-directory":
            target = tmp_path / f"content-{n}" / "content.db"
        else:
            (tmp_path / f"content-{n}").mkdir()
            target = tmp_path / f"content-{n}" / "content.db"
        monkeypatch.setattr(config, "CONTENT_DB", str(target))

    fresh()
    monkeypatch.setattr(config_db, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(config_db, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(config_db, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app, raise_server_exceptions=False), fresh


#: A value for every path parameter a GET route takes, so the sweep can call
#: them all. A route with a parameter not named here fails the sweep loudly.
PATH_VALUES = {"word": "maja", "topic": "osastav", "item_id": "x", "lemma": "maja",
               "part": "lugemine", "page": "1",
               "source_id": "selges-keeles", "name": "x", "theme": "kodu", "code": "x",
               "level": "A2"}


class TestNothingReturns500WithoutACorpus:
    """Every topic and every GET route answers without a corpus, in each missing-corpus
    shape.
    """

    def test_every_topic_answers(self, corpusless):
        from eesti.curriculum import TOPICS

        client, fresh = corpusless
        failed = {}
        for topic in TOPICS:
            fresh()
            response = client.post("/api/practice", json={"topic": topic.id, "count": 3})
            if response.status_code == 500:
                failed[topic.id] = response.status_code
        assert not failed, sorted(failed)

    def test_every_get_route_answers(self, corpusless):
        """Routes from `eesti.api.ROUTERS` (not `app.routes`), with a count guard. Only 500
        fails: snapshot routes answer 503 without `STATE_TOKEN` by design.
        """
        import re

        from eesti import api

        client, fresh = corpusless
        failed, unnamed, checked = {}, set(), 0
        for router in api.ROUTERS:
            for route in router.routes:
                if "GET" not in getattr(route, "methods", ()):
                    continue
                params = re.findall(r"{(\w+)(?::\w+)?}", route.path)
                unnamed |= {p for p in params if p not in PATH_VALUES}
                path = re.sub(r"{(\w+)(?::\w+)?}", lambda m: PATH_VALUES.get(m.group(1), "x"), route.path)
                fresh()
                response = client.get(path)
                checked += 1
                if response.status_code == 500:
                    failed[route.path] = response.status_code
        assert checked > 30, f"only {checked} GET routes reached — the walk broke"
        assert not unnamed, f"give the sweep a value for {sorted(unnamed)}"
        assert not failed, sorted(failed)
