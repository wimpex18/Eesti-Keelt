"""Where a person read it, the app plays the person — and falls back to
synthesis everywhere else, without the page knowing the difference.
"""

from __future__ import annotations

import io
import wave

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import config, haaldus  # noqa: E402


def _wav() -> bytes:
    import array

    out = io.BytesIO()
    with wave.open(out, "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(16_000)
        clip.writeframes(array.array("h", [1000] * 8000).tobytes())
    return out.getvalue()


@pytest.fixture
def recorded(tmp_path, monkeypatch):
    """An audio store with one word form and one sentence in it."""
    monkeypatch.setattr(config, "AUDIO_DB", str(tmp_path / "audio.db"))
    conn = haaldus.connect(config.AUDIO_DB)
    with conn:
        conn.execute("INSERT INTO pronunciation"
                     " (form, tag, spoken, lemma, mime, audio, source)"
                     " VALUES ('koera','sg p','`koera','koer','audio/wav',?,'psv')",
                     (_wav(),))
        conn.execute("INSERT INTO sentence_audio (text, words, mime, audio, source)"
                     " VALUES ('Ma elan Tallinnas ja õpin eesti keelt.', 6,"
                     " 'audio/wav', ?, 'eki')",
                     (_wav(),))
    return conn


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)


class TestAWordForm:
    def test_the_recording_is_served_with_what_was_said(self, client, recorded):
        r = client.get("/api/pronounce?form=koera&tag=sg%20p")
        assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
        # The mark is the point: `koera` and `k`oera` are different words.
        assert "%60koera" == r.headers["x-spoken-form"]

    def test_a_form_nobody_read_is_a_404_not_an_error(self, client, recorded):
        assert client.get("/api/pronounce?form=puudub").status_code == 404

    def test_without_the_store_it_says_so(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "AUDIO_DB", str(tmp_path / "absent.db"))
        r = client.get("/api/pronounce?form=koera")
        assert r.status_code == 404 and "не загружены" in r.json()["detail"]


class TestASentence:
    def test_speak_plays_the_reader_when_there_is_one(self, client, recorded):
        r = client.post("/api/speak", json={"text": "Ma elan Tallinnas ja õpin eesti keelt."})
        assert r.status_code == 200 and r.headers["x-audio-source"] == "eki"

    def test_anything_else_falls_through_to_synthesis(self, client, recorded):
        """Offline in tests, so synthesis answers 503 — what matters is that it
        was asked, rather than a recording being passed off as one."""
        r = client.post("/api/speak", json={"text": "Seda lauset keegi ei lugenud."})
        assert r.status_code in (200, 503) and "x-audio-source" not in r.headers

    def test_dictation_prefers_the_sentences_a_person_read(self, client, recorded):
        body = client.get("/api/dictation/next?count=1&seed=1").json()
        assert [p["text"] for p in body["passages"]] == [
            "Ma elan Tallinnas ja õpin eesti keelt."]

    def test_dictation_still_works_with_no_recordings(self, client, tmp_path,
                                                      monkeypatch):
        monkeypatch.setattr(config, "AUDIO_DB", str(tmp_path / "absent.db"))
        body = client.get("/api/dictation/next?count=1&seed=1").json()
        assert body["passages"] and body["passages"][0]["text"]
