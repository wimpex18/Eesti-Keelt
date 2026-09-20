"""What code can honestly say about a spoken answer: how much was said, how
fast, and how sure the transcript looks. Never a score — the exam is paired.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import evidence  # noqa: E402
from eesti.learner import DOUBTFUL, speaking_practice, speech_signals  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)


class TestTheSignals:
    def test_a_real_answer_is_measured(self):
        pytest.importorskip("estnltk")
        got = speech_signals("Ma elan Tallinnas ja töötan siin", seconds=12)
        assert got["answered"] and got["wpm"] == 30.0
        assert got["unknown_share"] == 0.0 and not got["doubtful"]

    def test_a_false_start_is_not_an_answer(self):
        assert not speech_signals("Ee... ma", seconds=4)["answered"]

    def test_a_garbled_transcript_says_so(self):
        """Nonsense words mean the recogniser struggled; the numbers then
        describe the recogniser, not the learner."""
        pytest.importorskip("estnltk")
        got = speech_signals("blorki morki zzz qqq vurgle", seconds=10)
        assert got["unknown_share"] > DOUBTFUL and got["doubtful"]

    def test_without_a_duration_there_is_no_pace(self):
        assert speech_signals("Ma elan siin", seconds=0)["wpm"] is None

    def test_nothing_here_is_a_score(self):
        got = speech_signals("Ma elan Tallinnas", seconds=10)
        assert not {"score", "grade", "level", "correct"} & set(got)


class TestItReachesTheLogAndTheVerdict:
    def test_an_answer_is_recorded_with_its_signals(self, client):
        client.post("/api/speaking/feedback", json={
            "transcript": "Ma elan Tallinnas ja õpin eesti keelt",
            "question": "Kus sa elad?", "seconds": 14})
        with evidence.connect() as log:
            ev = [e for e in evidence.events(log) if e.type == "speech"][-1]
        assert ev.payload["answered"] and ev.payload["wpm"]
        assert "doubtful" in ev.payload

    def test_the_practice_summary_counts_both_kinds(self, client):
        client.post("/api/speaking/feedback", json={
            "transcript": "Ma elan Tallinnas ja õpin", "seconds": 10})
        client.post("/api/transcribe/text?target=Ma%20loen",
                    json={"text": "Ma loen", "engine": "test"})
        with evidence.connect() as log:
            got = speaking_practice(log)
        assert got["answers"] == 1 and got["read_alouds"] == 1
        assert got["median_wpm"]

    def test_readiness_reports_the_practice_without_judging_it(self, client):
        before = next(p for p in client.get("/api/readiness/A2").json()["parts"]
                      if p["id"] == "raakimine")
        assert before["evidence"].startswith("не измеряется")
        client.post("/api/speaking/feedback", json={
            "transcript": "Ma elan Tallinnas ja õpin eesti keelt", "seconds": 14})
        after = next(p for p in client.get("/api/readiness/A2").json()["parts"]
                     if p["id"] == "raakimine")
        assert "за 90 дней" in after["evidence"] and "ответ" in after["evidence"]
        # Still not a verdict: the app cannot judge a paired exam part.
        assert after["touched"] is None
