"""The bounded tutor: grounded context in, a Russian explanation out, and an
answer that invents an Estonian form is dropped before the learner sees it.
"""

from __future__ import annotations

import json

import pytest

from eesti import tutor


@pytest.fixture
def says(monkeypatch):
    """Make every LLM lane answer with whatever the test wants."""
    def answer(text: str, *, available: bool = True):
        from eesti.providers import llm

        monkeypatch.setattr(llm, "complete",
                            lambda *a, **k: json.dumps({"explanation_ru": text}))
        for lane in llm.PROVIDERS.values():
            monkeypatch.setattr(type(lane), "available", property(lambda self: available),
                                raising=False)
    return answer


class TestGrounding:
    def test_an_invented_form_is_dropped_and_the_rule_stands(self, says):
        pytest.importorskip("estnltk")
        says("Здесь нужен osastav: **raamatuu** — это форма партитива.")
        got = tutor.explain_concept("obj-case")
        assert got.explanation_ru == "" and got.degraded
        assert "Vabamorf" in got.note and got.reference["known"]

    def test_a_grounded_explanation_is_kept(self, says):
        pytest.importorskip("estnltk")
        says("Действие завершено, поэтому нужен omastav: raamatu.")
        got = tutor.explain_concept("obj-case")
        assert "omastav" in got.explanation_ru and not got.degraded
        assert got.to_dict()["source"] == "model"
        assert got.engine.startswith("llm:")

    def test_a_topic_without_a_handbook_section_is_not_explained(self, says):
        says("что угодно")
        got = tutor.explain_concept("kusisonad")
        assert got.degraded and got.explanation_ru == "" and got.reference is None

    def test_no_engine_says_so_rather_than_guessing(self, says):
        says("не должно появиться", available=False)
        got = tutor.explain_concept("obj-case")
        assert got.engine == "none" and got.degraded


class TestExplainingAnAttempt:
    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx2")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def _a_miss(self, client) -> str:
        from eesti import evidence

        it = client.post("/api/practice", json={"topic": "tingiv", "count": 1}
                         ).json()["items"][0]
        client.post("/api/practice/answer", json={
            "topic": "tingiv", "prompt": "", "answer": "", "given": "vale",
            "token": it["token"]})
        with evidence.connect() as log:
            return [e for e in evidence.events(log) if e.type == "attempt"][-1].id

    def test_it_explains_the_attempt_the_log_kept(self, client, says):
        pytest.importorskip("estnltk")
        event_id = self._a_miss(client)
        says("Нужна форма tingiv kõneviis.")
        body = client.post("/api/tutor", json={"intent": "explain_attempt",
                                               "event_id": event_id}).json()
        assert body["explanation_ru"].startswith("Нужна форма")
        assert body["source"] == "model"

    def test_an_unknown_attempt_is_a_404(self, client):
        r = client.post("/api/tutor", json={"intent": "explain_attempt",
                                            "event_id": "nope"})
        assert r.status_code == 404

    def test_an_unknown_intent_is_a_400(self, client):
        assert client.post("/api/tutor", json={"intent": "grade_me"}).status_code == 400

    def test_the_tutor_never_records_anything(self, client, says):
        pytest.importorskip("estnltk")
        from eesti import evidence

        event_id = self._a_miss(client)
        says("Объяснение.")
        with evidence.connect() as log:
            before = len(evidence.events(log))
        client.post("/api/tutor", json={"intent": "explain_attempt",
                                        "event_id": event_id})
        with evidence.connect() as log:
            assert len(evidence.events(log)) == before
