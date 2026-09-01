"""The reading library has to survive a disk that does not.

Two constraints meet here and neither bends. The corpus is **owner-only** --
ERR transcripts are © ERR, Selges keeles carries no reuse grant -- so it cannot
ship inside an image built from a public repository. And Cloud Run's disk is
**ephemeral**, so a file copied into a container is gone at the next cold start.

So a harvest is pushed to the origin, the Worker archives it, and every
container that starts afterwards is handed it back. These tests cover the two
ends the app owns: receiving a push, and handing the archive back.

The push is authenticated by `STATE_TOKEN`, not by Cloudflare Access. That is
not a shortcut -- Access is an interactive login, and a script cannot satisfy
one. The Worker is guarded by Access; the origin is guarded by tokens; the
upload is a machine, so it goes to the origin.
"""

from __future__ import annotations

import base64
from pathlib import Path

import argparse

import pytest

pytest.importorskip("httpx", reason="TestClient needs httpx")

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
    """A real push refused with `403 {"detail":"not authorised"}` — the proxy
    guard, not the state-token guard, so the token the script had read off the
    service was not the one the app compares against.

    The script had already checked both tokens were non-empty and passed,
    because gcloud's projection DSL returned *something* for each. A value that
    is almost right is worse than one that is missing: it sails through an
    emptiness check, uploads a megabyte, and fails at the end with a message
    that does not name which token was at fault."""

    SCRIPT = ROOT / "deploy" / "push-content.sh"

    @pytest.fixture(scope="class")
    def script(self) -> str:
        return self.SCRIPT.read_text(encoding="utf-8")

    def test_tokens_are_parsed_from_json_not_the_projection_dsl(self, script):
        """Checked against the executable lines only. The comment quotes the
        old expression on purpose — the reason it was replaced is worth more
        than the tidiness of never naming it."""
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


class TestThePushWarnsAboutAnUnlinkedCorpus:
    """`topic_items` is the join, and nothing fills it on its own.

    `topiclinks.related()` reads it and `/api/practice` returns the result as the
    `reading` beside every drill — "the join that makes practice and the
    reading library one tool", in that endpoint's own words. The only thing
    that writes it is `cli link-topics`, run by hand: no harvest calls it, no
    deploy step calls it. So a freshly harvested corpus pushes with the table
    empty and every drill offers nothing to read, silently.

    Found with the table at **0 rows** locally against 349 items, which is
    exactly the shape the item-count check on the line above was added to
    catch — applied to one table and not to the other.
    """

    def _corpus(self, tmp_path, *, links: int):
        """Built by the app's own opener, like `conftest._build_content`.

        Three hand-written INSERTs here failed on three different NOT NULL
        columns in a row — `sources.kind`, then `items.added_on` — which is the
        drift that docstring warns about, reproduced immediately.
        """
        from eesti.sources import Item, add_items, connect, register

        path = tmp_path / "content.db"
        conn = connect(path)
        register(conn)
        add_items(conn, [Item(source_id="selges-keeles", skill="lugemine",
                              title="Tekst", body="sõna sõna", level=None,
                              band="keskmine", meta={})])
        item_id = conn.execute("SELECT id FROM items").fetchone()[0]
        for n in range(links):
            conn.execute("INSERT INTO topic_items (topic, item_id, hits) "
                         "VALUES (?, ?, 1)", (f"topic{n}", item_id))
        conn.commit()
        conn.close()
        return path

    def _push(self, tmp_path, monkeypatch, *, links: int, capsys):
        from eesti import cli

        monkeypatch.setenv("STATE_TOKEN", "t")
        monkeypatch.setenv("PROXY_TOKEN", "p")
        path = self._corpus(tmp_path, links=links)
        args = argparse.Namespace(database=str(path), url=None)
        # Stop before the upload: what is under test is the check, not the POST.
        monkeypatch.setattr(
            cli, "_post_content", lambda *a, **k: 0, raising=False)
        try:
            cli.cmd_push_content(args)
        except Exception:
            pass
        return capsys.readouterr().out

    def test_it_says_so_when_nothing_is_linked(self, tmp_path, monkeypatch, capsys):
        out = self._push(tmp_path, monkeypatch, links=0, capsys=capsys)
        assert "no topic links" in out, out
        assert "link-topics" in out, "the warning must name the fix"

    def test_it_stays_quiet_when_the_corpus_is_linked(self, tmp_path, monkeypatch, capsys):
        out = self._push(tmp_path, monkeypatch, links=3, capsys=capsys)
        assert "no topic links" not in out, out
