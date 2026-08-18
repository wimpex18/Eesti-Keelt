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

from eesti import app as app_module  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client with its own learner state, so tests never touch data/."""
    monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(app_module, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(app_module, "VOCAB_DB", str(tmp_path / "v.db"))
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

    def test_a_topic_with_no_generator_is_a_400_not_a_500(self, client):
        r = client.post("/api/practice", json={"topic": "pohivormid"})
        assert r.status_code == 400
        assert "generator" in r.json()["detail"]

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
        before = client.get("/api/vocab").json()["known_total"]
        assert client.post("/api/vocab/known", json={"lemmas": ["raamat"]}).json() == {
            "marked": 1
        }
        assert client.get("/api/vocab").json()["known_total"] == before + 1

    def test_vocab_bands_are_returned(self, client):
        bands = client.get("/api/vocab").json()["bands"]
        assert bands and bands[0]["from"] == 1
