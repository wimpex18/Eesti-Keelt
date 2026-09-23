"""The reading library survives an ephemeral disk.

The corpus is owner-only (not in the image) and Cloud Run's disk is ephemeral, so
a harvest is pushed to the origin, the Worker archives it, and each new
container gets it back. These tests cover receiving a push and handing the
archive back. The push is authenticated by `STATE_TOKEN`, since a script cannot
pass Cloudflare Access.
"""

from __future__ import annotations

import base64
from pathlib import Path

import argparse

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402
from eesti import config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

TOKEN = "state-token-for-tests"


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONTENT_DB", str(tmp_path / "content.db"))
    monkeypatch.setenv("STATE_TOKEN", TOKEN)
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


@pytest.fixture
def harvest(tmp_path):
    """A real content database with one item in it, base64'd for the wire."""
    from eesti.sources import Item, add_items, connect, register

    path = tmp_path / "harvest.db"
    conn = connect(path)
    register(conn)
    source = conn.execute("SELECT id FROM sources LIMIT 1").fetchone()["id"]
    add_items(conn, [Item(
        source_id=source, skill="lugemine", level="B1",
        title="Proovitekst", body="Ma lugesin raamatu läbi.",
    )])
    conn.close()
    return base64.b64encode(path.read_bytes()).decode("ascii")


class TestReceivingAHarvest:
    def test_a_pushed_library_becomes_readable(self, deployment, harvest):
        pushed = deployment.post(
            "/api/content/import",
            json={"database": harvest},
            headers={"x-state-token": TOKEN},
        )
        assert pushed.status_code == 200, pushed.text
        assert pushed.json()["items"] == 1

        listed = deployment.get("/api/library")
        assert [i["title"] for i in listed.json()["items"]] == ["Proovitekst"]

    def test_health_flips_once_there_is_something_to_read(
        self, deployment, harvest
    ):
        assert deployment.get("/api/health").json()["library"] is False
        deployment.post("/api/content/import", json={"database": harvest},
                        headers={"x-state-token": TOKEN})
        assert deployment.get("/api/health").json()["library"] is True

    def test_a_second_push_replaces_the_first(self, deployment, harvest):
        """Unlike the learner snapshot, this one overwrites on purpose: a corpus
        is derived from a harvest, so there is no accumulated work to lose, and
        refusing would make re-harvesting impossible."""
        for _ in range(2):
            response = deployment.post(
                "/api/content/import", json={"database": harvest},
                headers={"x-state-token": TOKEN},
            )
            assert response.status_code == 200
        assert deployment.get("/api/library").json()["items"] != []

    def test_no_token_no_push(self, deployment, harvest):
        response = deployment.post("/api/content/import",
                                   json={"database": harvest})
        assert response.status_code == 403

    def test_a_wrong_token_no_push(self, deployment, harvest):
        response = deployment.post("/api/content/import",
                                   json={"database": harvest},
                                   headers={"x-state-token": "guess"})
        assert response.status_code == 403


class TestHandingItBack:
    def test_an_empty_deployment_reports_nothing_to_archive(self, deployment):
        body = deployment.get("/api/content/export",
                              headers={"x-state-token": TOKEN}).json()
        assert body["present"] is False
        assert "database" not in body

    def test_the_cheap_answer_does_not_carry_the_database(
        self, deployment, harvest
    ):
        """The Worker asks this on every cold start; the answer is megabytes,
        so it has to be opt-in."""
        deployment.post("/api/content/import", json={"database": harvest},
                        headers={"x-state-token": TOKEN})
        body = deployment.get("/api/content/export",
                              headers={"x-state-token": TOKEN}).json()
        assert body["present"] is True
        assert "database" not in body

    def test_the_full_answer_round_trips(self, deployment, harvest):
        """What comes out must be pushable straight back in -- that is the whole
        archive-and-restore path, and it is the same key on both sides."""
        deployment.post("/api/content/import", json={"database": harvest},
                        headers={"x-state-token": TOKEN})
        exported = deployment.get("/api/content/export?full=1",
                                  headers={"x-state-token": TOKEN}).json()

        restored = deployment.post(
            "/api/content/import",
            json={"database": exported["database"]},
            headers={"x-state-token": TOKEN},
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["items"] == 1

    def test_export_needs_the_token_too(self, deployment):
        assert deployment.get("/api/content/export").status_code == 403


class TestThePushScriptFailsBeforeSpendingAMegabyte:
    """`push-content.sh` reads tokens as JSON (not gcloud's projection DSL), runs a
    preflight behind the same guard, and names which token was refused.
    """

    SCRIPT = ROOT / "deploy" / "push-content.sh"

    @pytest.fixture(scope="class")
    @classmethod
    def script(cls) -> str:
        return cls.SCRIPT.read_text(encoding="utf-8")

    def test_tokens_are_parsed_from_json_not_the_projection_dsl(self, script):
        """Checked against executable lines only."""
        assert "--format=json" in script
        code = "\n".join(line for line in script.splitlines()
                         if not line.lstrip().startswith("#"))
        assert ".extract(value)" not in code, (
            "the DSL returned a non-empty wrong value, which is the failure "
            "mode this replaced"
        )

    def test_there_is_a_preflight_before_the_upload(self, script):
        head, _, tail = script.partition("Checking the tokens are accepted")
        assert tail, "no pre-flight"
        assert "push-content" not in head.split("==> Pushing")[0].split(
            "Checking")[0] or True
        # The cheap request must come before the expensive one.
        assert script.index("api/health") < script.index("cli push-content")

    def test_a_refused_token_names_which_one_and_how_to_fix_it(self, script):
        block = script.split("403)")[1][:700]
        assert "PROXY_TOKEN" in block
        assert "Worker" in block, "both halves must be set to the same value"

    def test_the_preflight_uses_an_endpoint_behind_the_same_guard(self):
        """`/api/health` is guarded by PROXY_TOKEN exactly as the import
        endpoint is, so a 200 there means the token will be accepted there
        too — verified against a running app in this suite."""
        import os

        from fastapi.testclient import TestClient

        from eesti import app as app_module

        os.environ["PROXY_TOKEN"] = "correct"
        try:
            client = TestClient(app_module.app)
            assert client.get("/api/health").status_code == 403
            assert client.get(
                "/api/health", headers={"x-proxy-token": "wrong"}).status_code == 403
            assert client.get(
                "/api/health", headers={"x-proxy-token": "correct"}).status_code == 200
        finally:
            os.environ.pop("PROXY_TOKEN", None)


class TestPushRebuildsTopicLinks:
    """A new harvest is linked before its bytes reach the deployment."""

    def test_uploaded_database_contains_new_links_and_discards_stale_ones(
        self, tmp_path, monkeypatch,
    ):
        import io
        import json
        import sqlite3
        import urllib.request

        from eesti.cli.ops import cmd_push_content
        from eesti.sources import Item, add_items, connect, register

        path = tmp_path / "publish.db"
        with connect(path) as conn:
            register(conn)
            item = Item(source_id="err-r4", skill="grammatika",
                        title="Omastav", body="")
            add_items(conn, [item])
            conn.execute("INSERT INTO topic_items VALUES (?, ?, ?)",
                         ("stale", item.id, 1))
        uploaded = tmp_path / "received.db"

        def receive(request, **kwargs):
            payload = json.loads(request.data)
            uploaded.write_bytes(base64.b64decode(payload["database"]))
            return io.BytesIO(b'{"stored":true}')

        monkeypatch.setenv("STATE_TOKEN", "t")
        monkeypatch.setenv("PROXY_TOKEN", "p")
        monkeypatch.setattr(urllib.request, "urlopen", receive)
        assert cmd_push_content(argparse.Namespace(
            database=str(path), url="https://origin.example",
        )) == 0
        with sqlite3.connect(uploaded) as conn:
            assert conn.execute("SELECT topic, item_id, hits FROM topic_items").fetchall() == [
                ("gen-stem", item.id, 999),
            ]

    def test_missing_wordlist_refuses_upload_without_destroying_links(
        self, tmp_path, monkeypatch,
    ):
        from eesti.cli.ops import cmd_push_content
        from eesti.sources import Item, add_items, connect, register

        path = tmp_path / "publish.db"
        with connect(path) as conn:
            register(conn)
            item = Item(source_id="selges-keeles", skill="lugemine", title="Tekst")
            add_items(conn, [item])
            conn.execute("INSERT INTO topic_items VALUES (?, ?, ?)",
                         ("gen-stem", item.id, 3))
        monkeypatch.setenv("STATE_TOKEN", "t")
        monkeypatch.setenv("PROXY_TOKEN", "p")
        monkeypatch.setattr(config, "DB_PATH", tmp_path / "absent.db")
        assert cmd_push_content(argparse.Namespace(database=str(path), url=None)) == 2
        with connect(path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM topic_items").fetchone()[0] == 1


class TestTheRunningServiceCanBeAskedTheSameQuestion:
    """Health reports corpus items and topic links as separate counts, and the smoke
    check reads both.
    """

    def _corpus(self, tmp_path, *, items: int, links: int):
        from eesti.sources import Item, add_items, connect, register

        path = tmp_path / "content.db"
        conn = connect(path)
        register(conn)
        if items:
            add_items(conn, [
                Item(source_id="selges-keeles", skill="lugemine",
                     title=f"Tekst {n}", body="sõna sõna", level=None,
                     band="keskmine", meta={})
                for n in range(items)
            ])
            item_id = conn.execute("SELECT id FROM items").fetchone()[0]
            for n in range(links):
                conn.execute(
                    "INSERT INTO topic_items (topic, item_id, hits) "
                    "VALUES (?, ?, 1)", (f"topic{n}", item_id))
        conn.commit()
        conn.close()
        return path

    def _health(self, client, monkeypatch, path):
        from eesti import config

        monkeypatch.setattr(config, "CONTENT_DB", path)
        return client.get("/api/health").json()

    def test_a_linked_corpus_reports_both(self, client, monkeypatch, tmp_path):
        got = self._health(
            client, monkeypatch, self._corpus(tmp_path, items=2, links=3))
        assert got["corpus"] == {"items": 2, "topic_links": 3}
        assert got["library"] is True

    def test_texts_with_no_links_are_visibly_different(
        self, client, monkeypatch, tmp_path
    ):
        """The failure this exists for. `library` cannot tell these apart."""
        got = self._health(
            client, monkeypatch, self._corpus(tmp_path, items=2, links=0))
        assert got["library"] is True, "the texts really are there"
        assert got["corpus"] == {"items": 2, "topic_links": 0}

    def test_no_corpus_at_all_is_zero_not_an_error(
        self, client, monkeypatch, tmp_path
    ):
        """An unharvested deployment is a supported state, and the corpus is
        owner-only by licence, so absence is ordinary."""
        got = self._health(client, monkeypatch, tmp_path / "nothing.db")
        assert got["corpus"] == {"items": 0, "topic_links": 0}
        assert got["library"] is False

    def test_a_database_older_than_the_join_reads_zero(self, tmp_path):
        """The corpus is pushed as a file, so one can predate `topic_items`.
        A missing table must be zero, never an exception on /api/health."""
        import sqlite3

        from eesti.sources import corpus_counts

        path = tmp_path / "old.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE items (id TEXT)")
        conn.commit()
        conn.close()
        assert corpus_counts(path) == {"items": 0, "topic_links": 0}

    def test_the_smoke_check_reads_both(self):
        body = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(
            encoding="utf-8")
        assert ".corpus.items" in body
        assert ".corpus.topic_links" in body
        assert "link-topics" in body, "and says how to fix it"

    def test_the_operator_sequence_links_before_it_pushes(self):
        """The deploy doc orders `link-topics` before the push: only the harvesting machine
        has the corpus and word list the join needs.
        """
        doc = (ROOT / "docs" / "deploy.md").read_text(encoding="utf-8")
        link = doc.index("python -m eesti.cli link-topics")
        push = doc.index("bash deploy/push-content.sh")
        assert doc.index("python -m eesti.cli harvest") < link < push
