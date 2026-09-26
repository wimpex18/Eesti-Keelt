"""The home speech service the Worker reaches on the owner's Mac mini."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from eesti import asrserver
from eesti.providers.asr import Transcript


@pytest.fixture
def home(monkeypatch):
    from eesti.evals import asr_voxtral

    monkeypatch.setenv("HOME_ASR_TOKEN", "s3cret")
    monkeypatch.setenv("VOXTRAL_RT_MODEL", "/nowhere")
    monkeypatch.setattr(asr_voxtral, "transcribe",
                        lambda audio: Transcript("Ma ostsin uus auto.", "voxtral-rt"))
    return TestClient(asrserver.app)


def test_a_recording_without_the_secret_is_refused(home):
    assert home.post("/transcribe", content=b"audio").status_code == 403
    assert home.post("/transcribe", content=b"audio",
                     headers={"x-home-asr-token": "guess"}).status_code == 403


def test_no_configured_secret_is_a_refusal_not_an_open_door(home, monkeypatch):
    monkeypatch.delenv("HOME_ASR_TOKEN")
    assert home.post("/transcribe", content=b"audio",
                     headers={"x-home-asr-token": ""}).status_code == 403


def test_the_words_come_back_unjudged(home):
    got = home.post("/transcribe", content=b"audio", headers={"x-home-asr-token": "s3cret"})
    assert got.json() == {"text": "Ma ostsin uus auto.", "engine": "voxtral-rt"}


def test_empty_audio_is_rejected(home):
    assert home.post("/transcribe", content=b"",
                     headers={"x-home-asr-token": "s3cret"}).status_code == 400


def test_health_says_whether_the_model_is_loaded(home):
    body = home.get("/health").json()
    assert set(body) == {"ok", "engine", "loaded", "error"}


def test_the_worker_falls_back_to_whisper_and_never_waits_forever():
    from pathlib import Path

    worker = (Path(__file__).resolve().parents[1] / "deploy" / "worker.ts").read_text()
    assert "HOME_TIMEOUT_MS" in worker and "AbortSignal.timeout(HOME_TIMEOUT_MS)" in worker
    assert "if (!text && env.AI)" in worker, "Whisper answers whenever the Mac does not"
