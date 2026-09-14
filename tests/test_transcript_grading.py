"""Grading a transcript stays in the app and stays deterministic.

The Worker's AI binding returns only what Whisper heard; the target sentence is
known here, so the comparison is string alignment, not a model's opinion
(`docs/ai-boundaries.md`).
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


def post(client, text, target=None, **extra):
    url = "/api/transcribe/text" + (f"?target={target}" if target else "")
    response = client.post(url, json={"text": text, "engine": "test", **extra})
    assert response.status_code == 200, response.text
    return response.json()


class TestTranscriptGrading:
    def test_a_perfect_reading_scores_perfectly(self, client):
        said = "Ma lugesin raamatu läbi"
        body = post(client, said, target=said)
        assert body["comparison"]["ratio"] == 1.0
        assert body["comparison"]["missed"] == []

    def test_a_wrong_word_is_located_not_just_counted(self, client):
        """The learner has to see *which* word, or the score teaches nothing."""
        body = post(client, "Ma lugesin raamatut läbi", target="Ma lugesin raamatu läbi")
        comparison = body["comparison"]
        assert comparison["ratio"] < 1.0
        assert comparison["missed"] == ["raamatu"]

    def test_the_caveat_travels_with_the_score(self, client):
        """A miss can mean bad pronunciation or a recogniser that does not know
        accented Estonian, and the learner is never told which. The score is
        never shown without that sentence attached."""
        body = post(client, "Ma lugesin raamatu läbi", target="Ma lugesin raamatu läbi")
        assert body["comparison"]["caveat"]

    def test_no_target_means_no_comparison(self, client):
        """Free speech has nothing to compare against; inventing one would be a
        judgement, which is exactly what this endpoint refuses to make."""
        assert "comparison" not in post(client, "Ma räägin eesti keelt")

    def test_an_empty_transcript_is_not_graded_as_zero(self, client):
        """Silence, or a recogniser that failed, is not a wrong answer."""
        body = post(client, "", target="Ma lugesin raamatu läbi", degraded=True)
        assert "comparison" not in body
        assert body["degraded"] is True

    def test_the_engine_is_reported_back(self, client):
        """The UI names which engine answered, so a degraded run is visible."""
        assert post(client, "tere", target="tere")["engine"] == "test"

    def test_the_guard_covers_it(self, client, monkeypatch):
        """It writes nothing, but it is still origin surface behind the Worker."""
        monkeypatch.setenv("PROXY_TOKEN", "s3cret")
        response = client.post("/api/transcribe/text", json={"text": "tere"})
        assert response.status_code == 403
