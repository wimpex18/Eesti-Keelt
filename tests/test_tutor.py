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


class TestTheConversation:
    """The exam is paired, so practice has two sides — and the partner never
    corrects, never grades, and never passes off a form Vabamorf rejects."""

    @pytest.fixture
    def task(self):
        from eesti.speaking import bank

        return bank()[0].question

    @pytest.fixture
    def replies(self, monkeypatch):
        def answer(reply_et: str, hint_ru: str = ""):
            from eesti.providers import llm

            monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(
                {"reply_et": reply_et, "hint_ru": hint_ru}))
            for lane in llm.PROVIDERS.values():
                monkeypatch.setattr(type(lane), "available",
                                    property(lambda self: True), raising=False)
        return answer

    def test_it_answers_in_estonian_and_asks_back(self, task, replies):
        replies("Tere! Mina olen Mari. Kust sa pärit oled?", "Скажи, откуда ты.")
        got = tutor.converse(task, [])
        assert got.reply_et.startswith("Tere") and got.hint_ru
        assert got.to_dict()["graded"] is False and got.to_dict()["source"] == "model"

    def test_a_reply_in_russian_is_not_the_partners_turn(self, task, replies):
        replies("Привет! Расскажи о себе.")
        got = tutor.converse(task, [])
        assert got.reply_et == "" and got.degraded

    def test_forms_vabamorf_rejects_are_named_not_hidden(self, task, replies):
        pytest.importorskip("estnltk")
        replies("Ma elan Tallinnas ja mulle meeldib blorkimine.")
        got = tutor.converse(task, [])
        assert got.reply_et and "blorkimine" in got.unknown

    def test_the_exchange_is_capped(self, task, replies):
        replies("Jah.")
        history = [tutor.Turn("learner", "Tere") for _ in range(tutor.MAX_TURNS + 1)]
        got = tutor.converse(task, history)
        assert got.reply_et == "" and got.degraded and "15 минут" in got.note

    def test_an_unknown_task_is_refused(self, replies):
        replies("Tere")
        with pytest.raises(KeyError):
            tutor.converse("no such card", [])


class TestOneBoundary:
    """ADR-0002: every model-facing job goes through `tutor`."""

    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx2")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def test_the_writing_check_goes_through_the_tutor(self, client, monkeypatch):
        seen = {}

        def fake(text):
            seen["text"] = text
            return {"engine": "test", "degraded": False, "corrections": [],
                    "note": "", "diagnostics": "", "advisory": False,
                    "back_translation": None}

        monkeypatch.setattr(tutor, "check_writing", fake)
        body = client.post("/api/check", json={"text": "Ma elan siin."}).json()
        assert seen["text"] == "Ma elan siin." and body["engine"] == "test"

    def test_speaking_feedback_goes_through_the_tutor(self, client, monkeypatch):
        seen = {}

        def fake(transcript):
            seen["transcript"] = transcript
            return {"engine": "test", "degraded": False, "advisory": True,
                    "corrections": [], "note": "", "diagnostics": ""}

        monkeypatch.setattr(tutor, "speaking_feedback", fake)
        body = client.post("/api/speaking/feedback",
                           json={"transcript": "Ma elan siin"}).json()
        assert seen["transcript"] == "Ma elan siin" and body["advisory"]

    def test_a_conversation_turn_is_practice_evidence_never_a_score(
            self, client, monkeypatch):
        from eesti import evidence
        from eesti.providers import llm
        from eesti.speaking import bank

        monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(
            {"reply_et": "Väga hea. Kus sa töötad?"}))
        for lane in llm.PROVIDERS.values():
            monkeypatch.setattr(type(lane), "available", property(lambda self: True),
                                raising=False)
        body = client.post("/api/tutor", json={
            "intent": "converse", "task": bank()[0].question,
            "said": "Ma olen Sergei ja ma elan Tallinnas."}).json()
        assert body["reply_et"] and body["graded"] is False
        with evidence.connect() as log:
            ev = [e for e in evidence.events(log) if e.type == "conversation"][-1]
        assert ev.payload["turns"] == 1 and ev.payload["words"] == 7
        assert "said" not in ev.payload and "reply" not in ev.payload

    def test_the_tutor_spends_the_lane_s_daily_budget(self, client, monkeypatch):
        from eesti.providers import budget, llm

        monkeypatch.setattr(llm, "complete", lambda *a, **k: json.dumps(
            {"explanation_ru": "Объяснение."}))
        for lane in llm.PROVIDERS.values():
            monkeypatch.setattr(type(lane), "available", property(lambda self: True),
                                raising=False)
        import sqlite3

        from eesti import config

        budget.bind(sqlite3.connect(config.PROGRESS_DB))
        try:
            before = sum(budget.spent(f"llm:{n}") for n in ("local", "workers-ai",
                                                            "nvidia", "mistral",
                                                            "openrouter"))
            tutor.explain_concept("obj-case")
            after = sum(budget.spent(f"llm:{n}") for n in ("local", "workers-ai",
                                                           "nvidia", "mistral",
                                                           "openrouter"))
            assert after == before + 1
        finally:
            budget.bind(None)


def test_tutor_outage_trips_shared_breaker_without_retries(monkeypatch):
    from eesti.providers import breaker, grammar, llm

    calls = []
    monkeypatch.setattr(type(llm.PROVIDERS["workers-ai"]), "available", property(lambda self: True))
    def unavailable(name, *args, **kwargs):
        assert kwargs["attempts"] == 1
        calls.append(name)
        raise TimeoutError()
    monkeypatch.setattr(llm, "complete", unavailable)
    for _ in range(3):
        assert tutor._ask("test", set(), "test", None).degraded
    assert len(calls) == 2 * len(grammar.LLM_PREFERENCE)
    assert all(breaker.is_open(f"llm:{name}") for name in grammar.LLM_PREFERENCE)


def test_tutor_malformed_field_degrades_instead_of_crashing(monkeypatch):
    from eesti.providers import llm

    monkeypatch.setattr(type(llm.PROVIDERS["workers-ai"]), "available", property(lambda self: True))
    monkeypatch.setattr(llm, "complete", lambda *args, **kwargs: '{"explanation_ru": ["invalid"]}')
    assert tutor._ask("test", set(), "test", None).degraded
