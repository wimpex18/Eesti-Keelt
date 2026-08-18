"""The speaking bank and the ASR chain.

Both are shaped by one fact: the B1 speaking exam is paired, so nothing here
scores anything. The tests protect that boundary as much as the behaviour.
"""

from __future__ import annotations

import json

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
    @pytest.fixture(autouse=True)
    def _no_engines(self, monkeypatch):
        for key in ("HF_TOKEN", "OPENROUTER_API_KEY", "CLOUDFLARE_API_TOKEN",
                    "CLOUDFLARE_ACCOUNT_ID"):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setattr(asr, "_whisper_cpp_paths", lambda: (None, None))

    def test_with_nothing_configured_it_refuses_out_loud(self):
        """Silence would look like a broken button; the tab is useful without
        a transcript and should say why there isn't one."""
        result = asr.transcribe(b"not audio")
        assert result.text == ""
        assert result.degraded and result.note

    def test_available_reports_what_this_deployment_can_do(self):
        got = asr.available()
        assert got["ready"] is False and got["cloudflare"] is False
        assert got["estonian_model"].startswith("TalTechNLP/")

    def test_cloudflare_credentials_are_enough(self, monkeypatch):
        """The platform the app deploys to, with credentials the eval already
        provisions — which is why it is the primary."""
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a")
        got = asr.available()
        assert got["cloudflare"] and got["ready"] and got["hosted"]

    def test_half_the_cloudflare_credentials_is_not_enough(self, monkeypatch):
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
        assert asr.available()["cloudflare"] is False

    def test_cloudflare_is_tried_before_everything_else(self, monkeypatch):
        """Ordered by where the app runs, not by which engine is best in the
        abstract: a Cloudflare deployment has no laptop."""
        monkeypatch.setattr(
            asr, "_cloudflare",
            lambda audio, context="": asr.Transcript("pilv", "workers-ai"),
        )
        monkeypatch.setattr(
            asr, "_local",
            lambda audio, suffix=".wav": asr.Transcript("kohalik", "whisper.cpp"),
        )
        assert asr.transcribe(b"audio").text == "pilv"

    def test_a_failing_engine_falls_through_to_the_next(self, monkeypatch):
        """Unlike the grammar chain there is no offline engine behind this, so a
        hiccup must not end the attempt."""
        monkeypatch.setattr(
            asr, "_cloudflare",
            lambda audio, context="": asr.Transcript("", "workers-ai", True, "boom"),
        )
        monkeypatch.setattr(
            asr, "_openrouter",
            lambda audio, mime="audio/wav", context="": asr.Transcript("teine", "or"),
        )
        assert asr.transcribe(b"audio").text == "teine"

    def test_the_first_failure_is_reported_when_everything_fails(self, monkeypatch):
        monkeypatch.setattr(
            asr, "_cloudflare",
            lambda audio, context="": asr.Transcript("", "workers-ai", True, "boom"),
        )
        result = asr.transcribe(b"audio")
        assert result.degraded and "boom" in result.note

    def test_an_unconfigured_engine_is_skipped_not_treated_as_failure(self):
        """`None` means "no credentials", which must not shadow a later engine."""
        assert asr._cloudflare(b"x") is None
        assert asr._openrouter(b"x") is None

    def test_estonian_is_pinned_not_guessed(self, monkeypatch):
        """A few seconds of accented Estonian is exactly what Whisper guesses
        wrong, so the language is sent explicitly."""
        seen = {}

        class FakeResp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b'{"result":{"text":"tere"}}'

        def fake_urlopen(req, timeout=None):
            seen.update(json.loads(req.data))
            return FakeResp()

        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "t")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a")
        monkeypatch.setattr(asr.urllib.request, "urlopen", fake_urlopen)
        got = asr._cloudflare(b"audio", context="Rääkige endast.")
        assert got.text == "tere"
        assert seen["language"] == "et" and seen["task"] == "transcribe"
        assert seen["initial_prompt"] == "Rääkige endast."

    def test_an_estonian_llm_cannot_be_used_for_this(self):
        """Stated in code because it is the obvious question: EstLLM is a text
        model with no audio encoder. The Estonian speech models are TalTech's,
        and nobody hosts them."""
        assert "whisper" in asr.CF_MODEL.lower()
        assert "TalTechNLP" in asr.ESTONIAN_MODEL

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
