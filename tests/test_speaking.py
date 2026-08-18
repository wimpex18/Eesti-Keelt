"""The speaking bank and the ASR chain.

Both are shaped by one fact: the B1 speaking exam is paired, so nothing here
scores anything. The tests protect that boundary as much as the behaviour.
"""

from __future__ import annotations

import pytest

from eesti import speaking
from eesti.providers import asr


class TestQuestionBank:
    def test_it_covers_all_three_exam_task_shapes(self):
        kinds = {q.kind for q in speaking.BANK}
        assert kinds == set(speaking.KINDS)

    def test_every_question_is_estonian_with_a_russian_hint(self):
        for q in speaking.BANK:
            assert q.question and q.hint_ru and q.topic
            assert q.question.endswith(("?", ".")), q.topic

    def test_filtering_by_kind(self):
        for kind in speaking.KINDS:
            got = speaking.bank(kind)
            assert got and {q.kind for q in got} == {kind}

    def test_the_paired_tasks_are_actually_paired_in_wording(self):
        """A solo prompt for a paired task would train the wrong thing."""
        agree = speaking.bank("kokkulepe")
        assert agree
        for q in agree:
            assert "kokku" in q.question.lower() or "koos" in q.question.lower()


class TestAsrChain:
    def test_with_nothing_configured_it_refuses_out_loud(self, monkeypatch):
        """Silence would look like a broken button; the tab is useful without
        a transcript and should say why there isn't one."""
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setattr(asr, "_whisper_cpp_paths", lambda: (None, None))
        result = asr.transcribe(b"not audio")
        assert result.text == ""
        assert result.degraded and result.note

    def test_available_reports_what_this_machine_can_do(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setattr(asr, "_whisper_cpp_paths", lambda: (None, None))
        got = asr.available()
        assert got["local"] is False and got["hosted"] is False
        assert got["estonian_model"].startswith("TalTechNLP/")

    def test_a_token_makes_the_hosted_engine_available(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "x")
        monkeypatch.setattr(asr, "_whisper_cpp_paths", lambda: (None, None))
        assert asr.available()["hosted"] is True

    def test_local_is_preferred_over_hosted(self, monkeypatch):
        """The accurate option is also the private one; it must win."""
        monkeypatch.setenv("HF_TOKEN", "x")
        monkeypatch.setattr(
            asr, "_local", lambda audio, suffix=".wav": asr.Transcript("kohalik", "whisper.cpp")
        )
        monkeypatch.setattr(
            asr, "_hosted", lambda audio, mime="audio/wav": asr.Transcript("pilv", "hf")
        )
        assert asr.transcribe(b"audio").text == "kohalik"

    def test_a_local_failure_is_reported_not_swallowed(self, monkeypatch):
        monkeypatch.setattr(
            asr, "_local",
            lambda audio, suffix=".wav": asr.Transcript("", "whisper.cpp", True, "boom"),
        )
        result = asr.transcribe(b"audio")
        assert result.degraded and "boom" in result.note

    def test_it_names_the_estonian_model_rather_than_a_generic_one(self):
        """The recommendation belongs next to the code that would use it."""
        assert "et-verbatim-2604" in asr.ESTONIAN_MODEL
        assert asr.ESTONIAN_GGML.endswith(".bin")


class TestApi:
    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def test_empty_audio_is_rejected(self, client):
        assert client.post("/api/transcribe", content=b"").status_code == 400

    def test_an_oversized_recording_is_rejected(self, client):
        r = client.post("/api/transcribe", content=b"0" * 12_000_001,
                        headers={"Content-Type": "audio/wav"})
        assert r.status_code == 413

    def test_no_engine_is_still_a_200(self, client, monkeypatch):
        """A missing engine is a degraded answer, not an error: the recording
        already happened and the learner must not lose it."""
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setattr(asr, "_whisper_cpp_paths", lambda: (None, None))
        r = client.post("/api/transcribe", content=b"xx",
                        headers={"Content-Type": "audio/wav"})
        assert r.status_code == 200 and r.json()["degraded"]

    def test_the_bank_is_served(self, client):
        data = client.get("/api/speaking").json()
        assert len(data["questions"]) == len(speaking.BANK)
        assert set(data["kinds"]) == set(speaking.KINDS)
