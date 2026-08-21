"""The HTTP surface for the curriculum path.

Steps 1-9 were terminal-only, which meant none of it was reachable from the
phone the app is meant to run on. These tests cover the endpoints that close
that gap, and in particular the two places where a client could be wrong: the
server, not the browser, decides whether an answer is correct and whether a
topic has been mastered.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx", reason="TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module
from eesti import config as _config  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client with its own learner state, so tests never touch data/."""
    monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(_config, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(app_module, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(_config, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(app_module, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.setattr(_config, "VOCAB_DB", str(tmp_path / "v.db"))
    return TestClient(app_module.app)


def _first_item(client, topic="tingiv"):
    body = client.post("/api/practice", json={"topic": topic, "count": 3, "seed": 1})
    assert body.status_code == 200, body.text
    data = body.json()
    assert data["items"], data
    return data, data["items"][0]


class TestCurriculum:
    def test_the_whole_path_is_returned_in_study_order(self, client):
        from eesti.curriculum import order

        data = client.get("/api/curriculum").json()
        assert [t["id"] for t in data["topics"]] == [t.id for t in order()]

    def test_it_names_where_to_resume(self, client):
        data = client.get("/api/curriculum").json()
        assert data["resume"]
        by_id = {t["id"]: t for t in data["topics"]}
        assert by_id[data["resume"]]["state"] in ("ready", "in progress")

    def test_locked_topics_say_what_blocks_them(self, client):
        data = client.get("/api/curriculum").json()
        locked = [t for t in data["topics"] if t["state"] == "locked"]
        assert locked
        assert all(t["blocked_by"] for t in locked)


class TestPractice:
    def test_it_returns_items_for_the_named_topic(self, client):
        data, item = _first_item(client)
        assert data["topic"] == "tingiv"
        assert item["prompt"] and item["answer"]

    def test_it_falls_back_to_where_the_learner_left_off(self, client):
        data = client.post("/api/practice", json={"count": 2, "seed": 1}).json()
        assert data["topic"] == client.get("/api/curriculum").json()["resume"]

    def test_a_theme_narrows_the_vocabulary(self, client):
        from eesti.themes import lemmas_for
        from eesti.wordlist import connect

        data = client.post("/api/practice", json={
            "topic": "lihtminevik", "theme": "reisimine", "count": 5, "seed": 1
        }).json()
        allowed = set(lemmas_for(connect(), "reisimine", pos="v"))
        assert data["items"]
        assert {i["lemma"] for i in data["items"]} <= allowed

    def test_a_topic_with_no_generator_answers_in_russian_rather_than_erroring(
            self, client):
        """It used to be a 400 carrying a Python exception message -- English,
        naming `docs/curriculum-plan.md`, rendered by the page as `Viga: ...`.

        The request is valid and the answer is "there is no exercise for this
        yet", which is the same shape as a topic whose corpus has not been
        uploaded: 200, no items, and a readable reason."""
        r = client.post("/api/practice", json={"topic": "lauseehitus"})
        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert "docs/" not in body["detail"]
        assert any("Ѐ" <= ch <= "ӿ" for ch in body["detail"]), body["detail"]

    def test_an_unknown_topic_is_still_an_error(self, client):
        """Distinct from the above: `lauseehitus` exists and has no drill;
        `nonesuch` is not a topic at all. Guarding the lookup is what keeps
        these two apart -- moving it above the try once turned this into a
        500."""
        r = client.post("/api/practice", json={"topic": "nonesuch"})
        assert r.status_code == 400

    def test_an_unknown_topic_is_a_400(self, client):
        assert client.post("/api/practice", json={"topic": "nonesuch"}).status_code == 400


class TestAnswering:
    def _answer(self, client, topic, item, given):
        return client.post("/api/practice/answer", json={
            "topic": topic, "prompt": item["prompt"], "answer": item["answer"],
            "given": given, "distractor": item.get("distractor", ""),
            "lemma": item.get("lemma", ""),
        }).json()

    def test_the_server_grades_not_the_client(self, client):
        """A browser that decides its own answers is a browser that can mark
        itself mastered."""
        _, item = _first_item(client)
        assert self._answer(client, "tingiv", item, item["answer"])["correct"]
        assert not self._answer(client, "tingiv", item, "ilmselgelt vale")["correct"]

    def test_answers_are_recorded_and_move_the_accuracy(self, client):
        _, item = _first_item(client)
        first = self._answer(client, "tingiv", item, item["answer"])
        assert first["accuracy"] == 1.0
        second = self._answer(client, "tingiv", item, "vale")
        assert second["accuracy"] == 0.5

    def test_a_missed_item_reaches_the_review_queue(self, client):
        _, item = _first_item(client)
        self._answer(client, "tingiv", item, "vale")
        assert client.get("/api/review/stats").json()["total"] >= 1

    def test_mastery_is_reported_by_the_server(self, client):
        from eesti.progress import MASTERY_WINDOW

        data = client.post(
            "/api/practice", json={"topic": "kusisonad", "count": 12, "seed": 1}
        ).json()
        results = [
            self._answer(client, "kusisonad", it, it["answer"])
            for it in data["items"][:MASTERY_WINDOW]
        ]
        assert results[-1]["mastered"]
        assert any(r["just_mastered"] for r in results)

    def test_mastering_seeds_the_review_queue(self, client):
        from eesti.progress import MASTERY_WINDOW

        data = client.post(
            "/api/practice", json={"topic": "kusisonad", "count": 12, "seed": 1}
        ).json()
        for item in data["items"][:MASTERY_WINDOW]:
            self._answer(client, "kusisonad", item, item["answer"])
        kinds = {
            r[0] for r in app_module.review_db().execute(
                "SELECT DISTINCT kind FROM review_items"
            )
        }
        assert "kusisonad" in kinds


class TestOtherSurfaces:
    def test_status_has_no_overall_number(self, client):
        data = client.get("/api/status").json()
        assert "overall" not in data["sections"]
        assert "no overall percentage" in data["note"]

    def test_themes_are_listed_with_their_usable_size(self, client):
        themes = client.get("/api/themes").json()["themes"]
        assert themes and all(t["usable"] <= t["declared"] for t in themes)

    def test_a_checkpoint_mixes_topics(self, client):
        data = client.get("/api/checkpoint/A1?count=8&seed=1").json()
        topics = [i["topic"] for i in data["items"]]
        assert len(set(topics)) >= 5
        assert all(a != b for a, b in zip(topics, topics[1:]))

    def test_an_unknown_level_is_a_404(self, client):
        assert client.get("/api/checkpoint/C2").status_code == 404

    def test_marking_a_word_known_is_explicit(self, client):
        """Read back through `/api/status`, which is where the vocabulary
        numbers are actually shown. `/api/vocab` returned the same figures to
        nobody — it had no caller anywhere, and a second route serving one
        screen is a second thing to keep in step."""
        def known():
            return client.get("/api/status").json()["sections"]["sonavara"][
                "known_in_top"]

        before = known()
        # Asserts the fields this test is about rather than the whole dict: the
        # response gained `status` when `eiran` became reachable, and an exact
        # comparison fails on an addition that breaks nothing.
        body = client.post("/api/vocab/known", json={"lemmas": ["raamat"]}).json()
        assert body["marked"] == 1
        assert known() >= before

    def test_vocab_bands_are_returned(self, client):
        bands = client.get("/api/status").json()["sections"]["sonavara"]["bands"]
        assert bands and bands[0]["from"] == 1


class TestStateSnapshots:
    """The endpoints that stop a Cloudflare deploy eating the learner's progress.

    Container disk is ephemeral — "when a Container instance goes to sleep, the
    next time it is started, it will have a fresh disk" — so mastery, the review
    queue and the vocabulary table have to be handed out and taken back.
    """

    @pytest.fixture
    def secured(self, client, monkeypatch):
        monkeypatch.setenv("STATE_TOKEN", "s3cret")
        return client

    def test_an_unset_token_refuses_rather_than_defaulting_open(self, client, monkeypatch):
        """An unset secret is a misconfiguration, not permission."""
        monkeypatch.delenv("STATE_TOKEN", raising=False)
        assert client.get("/api/state/export").status_code == 503

    def test_a_wrong_token_is_rejected(self, secured):
        r = secured.get("/api/state/export", headers={"x-state-token": "nope"})
        assert r.status_code == 403

    def test_export_returns_only_the_learners_databases(self, secured):
        """Not the word list, the form index or the harvested corpus: those are
        baked in or pushed separately, so shipping them would be 58 MB of
        copying something every container already has.

        `notion` is here because it holds queued corrections waiting for a
        person to review them. Leaving it out meant the queue was emptied by
        every cold start -- silently, which is how it went unnoticed."""
        data = secured.get("/api/state/export",
                           headers={"x-state-token": "s3cret"}).json()
        assert set(data["databases"]) == {"progress", "review", "vocab", "notion"}

    def test_a_snapshot_round_trips(self, secured, tmp_path, monkeypatch):
        import base64

        from eesti import app as app_module

        # Write something worth losing. It has to be a graded *answer*: asking
        # for items with an explicit topic never touches the progress database.
        items = secured.post(
            "/api/practice", json={"topic": "kusisonad", "count": 1, "seed": 1}
        ).json()["items"]
        secured.post("/api/practice/answer", json={
            "topic": "kusisonad", "prompt": items[0]["prompt"],
            "answer": items[0]["answer"], "given": items[0]["answer"],
        })
        blob = secured.get("/api/state/export",
                           headers={"x-state-token": "s3cret"}).json()
        assert blob["databases"]["progress"], "nothing was captured to restore"

        # A fresh container: new, empty paths. Redirected on `config`, which is
        # the single place the application resolves these from -- `app` used to
        # keep its own copies, and having two names for one file is how a
        # restore came to land somewhere the app did not read.
        from eesti import config as config_module

        fresh = {name: tmp_path / f"{name}.db" for name in ("progress", "review", "vocab")}
        for key, name in (("progress", "PROGRESS_DB"), ("review", "REVIEW_DB"),
                          ("vocab", "VOCAB_DB")):
            monkeypatch.setattr(config_module, name, str(fresh[key]))
            monkeypatch.setattr(app_module, name, str(fresh[key]), raising=False)

        restored = secured.post(
            "/api/state/import", json={"databases": blob["databases"]},
            headers={"x-state-token": "s3cret"},
        ).json()
        assert "progress" in restored["restored"]
        assert fresh["progress"].read_bytes() == base64.b64decode(
            blob["databases"]["progress"]
        )

        # And the restored attempt is really there, not just the bytes.
        import sqlite3

        assert sqlite3.connect(fresh["progress"]).execute(
            "SELECT COUNT(*) FROM attempts WHERE topic = 'kusisonad'"
        ).fetchone()[0] == 1

    def test_restore_refuses_to_overwrite_real_work(self, secured, tmp_path, monkeypatch):
        """A restore racing a learner who has already started would discard the
        newer work. Losing five minutes beats losing it silently."""
        import base64

        from eesti import app as app_module
        from eesti.progress import connect as progress_connect

        live = tmp_path / "progress.db"
        conn = progress_connect(live)
        conn.execute(
            "INSERT INTO attempts (topic,item_key,correct,answer,at)"
            " VALUES ('olevik','k',1,'x','now')"
        )
        conn.commit()
        monkeypatch.setattr(app_module, "PROGRESS_DB", str(live))
        monkeypatch.setattr(_config, "PROGRESS_DB", str(live))
        before = live.read_bytes()
        got = secured.post(
            "/api/state/import",
            json={"databases": {"progress": base64.b64encode(b"older").decode()}},
            headers={"x-state-token": "s3cret"},
        ).json()
        assert got["skipped"] == ["progress"] and got["restored"] == []
        assert live.read_bytes() == before

    def test_an_empty_schema_is_not_treated_as_work(self, secured, tmp_path, monkeypatch):
        """The bug this replaces, found by running the real container: a fresh
        instance served one request, which created progress.db with an empty
        schema, and the restore then refused to overwrite it — silently
        discarding the snapshot it existed to restore."""
        import base64

        from eesti import app as app_module
        from eesti.progress import connect as progress_connect

        empty = tmp_path / "progress.db"
        progress_connect(empty)                 # schema only, no attempts
        assert empty.stat().st_size > 0
        monkeypatch.setattr(app_module, "PROGRESS_DB", str(empty))
        monkeypatch.setattr(_config, "PROGRESS_DB", str(empty))
        snapshot = tmp_path / "snap.db"
        conn = progress_connect(snapshot)
        conn.execute(
            "INSERT INTO attempts (topic,item_key,correct,answer,at)"
            " VALUES ('olevik','k',1,'x','now')"
        )
        conn.commit()
        conn.close()

        got = secured.post(
            "/api/state/import",
            json={"databases": {
                "progress": base64.b64encode(snapshot.read_bytes()).decode()
            }},
            headers={"x-state-token": "s3cret"},
        ).json()
        assert got["restored"] == ["progress"]

        import sqlite3

        assert sqlite3.connect(empty).execute(
            "SELECT COUNT(*) FROM attempts"
        ).fetchone()[0] == 1

    def test_an_empty_entry_is_skipped_not_written(self, secured, tmp_path, monkeypatch):
        from eesti import app as app_module

        target = tmp_path / "vocab.db"
        monkeypatch.setattr(app_module, "VOCAB_DB", str(target))
        monkeypatch.setattr(_config, "VOCAB_DB", str(target))
        got = secured.post(
            "/api/state/import", json={"databases": {"vocab": ""}},
            headers={"x-state-token": "s3cret"},
        ).json()
        assert got["restored"] == [] and not target.exists()


class TestAnEmptyTopicSaysWhy:
    """Comparing two content.db files exposed this: with the older one,
    `sonajark` returned 200 with zero items and no `detail`, and the page can
    only print what it is given — so the learner saw a bare "midagi ei tulnud".

    "The corpus has not been uploaded yet" and "the generator is broken" are
    different problems and only one of them is the learner's to fix."""

    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        from fastapi.testclient import TestClient

        from eesti import app as app_module, config

        # A content store with the schema and nothing in it: exactly what a
        # deployment looks like before `push-content.sh` has been run.
        from eesti.sources import connect

        connect(tmp_path / "content.db")
        monkeypatch.setattr(config, "CONTENT_DB", str(tmp_path / "content.db"))
        monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
        monkeypatch.setattr(_config, "PROGRESS_DB", str(tmp_path / "p.db"))
        return TestClient(app_module.app)

    def test_a_corpus_topic_names_the_missing_corpus(self, client):
        got = client.post("/api/practice",
                          json={"topic": "sonajark", "count": 5}).json()
        assert got["items"] == []
        assert "push-content" in got["detail"]

    def test_the_reason_is_in_russian(self, client):
        """It is an instruction to act on, not a label."""
        detail = client.post("/api/practice",
                             json={"topic": "sonajark", "count": 5}).json()["detail"]
        assert any("Ѐ" <= ch <= "ӿ" for ch in detail)

    def test_a_topic_that_needs_no_corpus_does_not_blame_the_corpus(self, client):
        """`kusisonad` is generated from closed-class patterns and works with
        no corpus at all — telling the learner to upload one would be wrong."""
        got = client.post("/api/practice",
                          json={"topic": "kusisonad", "count": 5}).json()
        assert got["items"], "this topic should work without a corpus"
        assert got["detail"] is None

    def test_detail_is_always_present_in_the_payload(self, client):
        """The page reads `res.detail`; a key that only sometimes exists is a
        key the page cannot rely on."""
        got = client.post("/api/practice",
                          json={"topic": "kusisonad", "count": 5}).json()
        assert "detail" in got
