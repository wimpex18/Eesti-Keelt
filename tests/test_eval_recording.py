"""Recording the speech eval set: local only, and it writes what the eval reads.

ADR-0003: the set that decides which recogniser to use is the learner's own
voice, so the app has to be able to record it — on this machine, never on the
deployment.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti.evals import asr as evaluation  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from eesti.app import app

    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    monkeypatch.setattr(evaluation, "SET", tmp_path / "asr")
    return TestClient(app)


class TestItStaysLocal:
    def test_the_deployment_has_no_such_route(self, client, monkeypatch):
        """`PROXY_TOKEN` is set only where the Worker fronts the app. Past the
        origin guard (which answers 403 on its own), the routes are simply not
        there."""
        monkeypatch.setenv("PROXY_TOKEN", "deployed")
        through = {"x-proxy-token": "deployed"}
        assert client.get("/api/eval/available", headers=through).status_code == 404
        assert client.get("/api/eval/prompt", headers=through).status_code == 404
        assert client.post("/api/eval/clip?text=Tere", content=b"x",
                           headers=through).status_code == 404
        assert client.post("/api/eval/draft/0000", json={"text": "Tere", "engine": "x"},
                           headers=through).status_code == 404
        assert client.post("/api/eval/review/0000", json={
            "transcript": "Tere", "listened": True}, headers=through).status_code == 404
        # And without the Worker's token, nothing reaches the app at all.
        assert client.get("/api/eval/prompt").status_code == 403


class TestThePrompts:
    def test_local_recording_tool_is_available_without_a_prompt(self, client):
        assert client.get("/api/eval/available").json() == {"local": True}

    def test_a_plain_prompt_is_a_sentence_to_read(self, client):
        got = client.get("/api/eval/prompt?seed=1").json()
        assert got["text"] and got["planted"] == ""

    def test_a_planted_prompt_carries_the_wrong_form_and_names_it(self, client):
        got = client.get("/api/eval/prompt?planted=true&seed=1").json()
        assert got["planted"] and got["planted"] in got["text"]
        assert got["correct"] and got["correct"] not in got["text"]
        assert "как написано" in got["note"]


class TestTheClips:
    def _save(self, client, text="Ma loen raamatut", planted=""):
        q = f"?text={text.replace(' ', '%20')}" + (f"&planted={planted}" if planted else "")
        return client.post("/api/eval/clip" + q, content=b"RIFFxxxx",
                           headers={"Content-Type": "audio/wav"})

    def test_a_clip_is_written_with_what_was_read(self, client):
        body = self._save(client).json()
        assert body["clips"] == 1
        assert evaluation.clips(evaluation.SET) == []
        assert (evaluation.SET / "0000.prompt").read_text() == "Ma loen raamatut"
        assert (evaluation.SET / "0000.txt").read_text() == ""
        assert len(evaluation.inventory(evaluation.SET)[1]) == 1

    def test_a_planted_clip_records_the_word_said_wrong(self, client):
        self._save(client, "Ma ei ostnud pileti", planted="pileti")
        assert (evaluation.SET / "0000.said").read_text() == "pileti"

    def test_question_answer_waits_for_a_human_transcript(self, client):
        saved = client.post("/api/eval/clip?question=Kus%20te%20elate%3F",
                            content=b"RIFFxxxx",
                            headers={"Content-Type": "audio/wav"})
        assert saved.status_code == 200
        assert saved.json()["question"] is True
        assert (evaluation.SET / "0000.question").read_text() == "Kus te elate?"
        transcript = evaluation.SET / "0000.txt"
        assert transcript.read_text() == ""
        with pytest.raises(ValueError, match="cannot be empty"):
            evaluation.verify_clip(evaluation.SET / "0000.wav")

        draft = client.post("/api/eval/draft/0000",
                            json={"text": "Ma elan Tallinnas.", "engine": "workers-ai"})
        assert draft.status_code == 200
        assert "Ma elan Tallinnas" in (evaluation.SET / "0000.draft.json").read_text()
        assert transcript.read_text() == ""  # a model guess is not ground truth

        transcript.write_text("Ma elan Tallinnas.", encoding="utf-8")
        seal = evaluation.verify_clip(evaluation.SET / "0000.wav")
        assert seal["question"] == "Kus te elate?"
        assert len(evaluation.clips(evaluation.SET)) == 1

    def test_in_app_review_seals_only_a_listened_transcript(self, client):
        self._save(client)
        url = "/api/eval/review/0000"
        assert client.post(url, json={"transcript": "Ma loen raamatut"}).status_code == 400
        assert evaluation.clips(evaluation.SET) == []
        got = client.post(url, json={
            "transcript": "Ma loen raamatut", "listened": True})
        assert got.status_code == 200
        assert len(evaluation.clips(evaluation.SET)) == 1
        assert evaluation.clips(evaluation.SET)[0].said == "Ma loen raamatut"

    def test_in_app_review_checks_a_planted_form_against_actual_speech(self, client):
        saved = client.post("/api/eval/clip?text=Ma%20ei%20ostnud%20pileti"
                            "&planted=pileti&accepted=piletit", content=b"RIFFxxxx",
                            headers={"Content-Type": "audio/wav"})
        assert saved.status_code == 200
        url = "/api/eval/review/0000"
        missing = client.post(url, json={
            "transcript": "Ma ei ostnud piletit", "listened": True,
            "planted_said": True})
        assert missing.status_code == 400
        assert evaluation.clips(evaluation.SET) == []
        got = client.post(url, json={
            "transcript": "Ma ei ostnud pileti", "listened": True,
            "planted_said": True})
        assert got.status_code == 200 and got.json()["planted"] is True
        assert evaluation.clips(evaluation.SET)[0].annotation["accepted"] == "piletit"

    def test_clips_do_not_overwrite_each_other(self, client):
        for _ in range(3):
            self._save(client)
        assert len(evaluation.inventory(evaluation.SET)[1]) == 3

    def test_an_empty_recording_or_no_text_is_refused(self, client):
        assert client.post("/api/eval/clip?text=Tere", content=b"").status_code == 400
        assert self._save(client, text="").status_code == 400
        assert client.post("/api/eval/clip?text=Tere&question=Kus", content=b"RIFF",
                           headers={"Content-Type": "audio/wav"}).status_code == 400
        assert client.post("/api/eval/draft/oops",
                           json={"text": "Tere", "engine": "x"}).status_code != 200
