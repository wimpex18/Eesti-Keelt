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
        assert client.get("/api/eval/prompt", headers=through).status_code == 404
        assert client.post("/api/eval/clip?text=Tere", content=b"x",
                           headers=through).status_code == 404
        # And without the Worker's token, nothing reaches the app at all.
        assert client.get("/api/eval/prompt").status_code == 403


class TestThePrompts:
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
        assert (evaluation.SET / "0000.txt").read_text() == "Ma loen raamatut"
        assert len(evaluation.inventory(evaluation.SET)[1]) == 1

    def test_a_planted_clip_records_the_word_said_wrong(self, client):
        self._save(client, "Ma ei ostnud pileti", planted="pileti")
        assert (evaluation.SET / "0000.said").read_text() == "pileti"

    def test_clips_do_not_overwrite_each_other(self, client):
        for _ in range(3):
            self._save(client)
        assert len(evaluation.inventory(evaluation.SET)[1]) == 3

    def test_an_empty_recording_or_no_text_is_refused(self, client):
        assert client.post("/api/eval/clip?text=Tere", content=b"").status_code == 400
        assert self._save(client, text="").status_code == 400
