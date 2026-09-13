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

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402
from eesti import config as config_db
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


@pytest.fixture(params=["cannot-be-created", "no-directory", "directory-no-file"])
def corpusless(request, tmp_path, monkeypatch):
    """Every way a container meets the app without its corpus: a path SQLite
    cannot create; a directory that is not there (Cloud Run ignoring `VOLUME`);
    and the directory there with no file in it — the Docker image, and every
    cold start before the Worker restores the library. The last is the one that
    answered 500: SQLite creates the file, empty, with no tables.

    Returns `(client, fresh)`. `fresh()` points the app at a new, untouched
    path of the same kind, and the sweep calls it before **every** request:
    opening the corpus through `sources.connect` creates its tables, so one
    request can repair the path for the next, and a sweep sharing one path
    passed while the first `osastav` of a cold container failed.
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
               "source_id": "selges-keeles", "name": "x", "theme": "kodu", "code": "x",
               "level": "A2"}


class TestNothingReturns500WithoutACorpus:
    """`POST /api/practice {"topic": "osastav"}` answered 500 in the built image
    (2026-09-14): `practice._content` opened the corpus with a bare
    `sqlite3.connect`, which creates an empty file with no tables, and
    `cloze.sentences` asked it for `items`. Every other opener applies its
    schema; this one did not, and no test called that topic without a corpus.
    So: every topic, and every GET route, both ways a corpus can be missing."""

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
        """From `eesti.api.ROUTERS`, not `app.routes`: FastAPI keeps an included
        router as one lazy entry, and the first version of this sweep walked
        `app.routes`, found no API route at all, and passed. The count below is
        the guard on the guard.

        500 only: the snapshot routes answer 503 "STATE_TOKEN is not
        configured" on purpose — an unset secret is a refusal, not a crash."""
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
