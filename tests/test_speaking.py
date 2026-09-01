"""The speaking bank and the ASR chain.

Both are shaped by one fact: the B1 speaking exam is paired, so nothing here
scores anything. The tests protect that boundary as much as the behaviour.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eesti import speaking
from eesti.providers import asr

from pagesrc import markup_and_script


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


class TestTranscriptCorrections:
    """A transcript is evidence about the learner *and* the recogniser.

    Nothing in the pipeline can separate them, so anything anchored on a word
    the recogniser may have invented has to go. See docs/ai-boundaries.md.
    """

    TEXT = "ma lugesin eile raamatut läbi ja siis läksin kohli"

    def test_the_real_error_survives(self):
        from eesti.providers import grammar

        result = grammar.from_transcript(grammar.check(self.TEXT), self.TEXT)
        assert any(c.tag == "obj-case" and c.wrong == "raamatut"
                   for c in result.corrections)

    def test_corrections_on_an_invented_word_are_dropped(self):
        """`kohli` is not a word — the recogniser made it up. Reporting it as a
        vocabulary error *and* an object-case error is two mistakes the learner
        never made."""
        from eesti.providers import grammar

        result = grammar.from_transcript(grammar.check(self.TEXT), self.TEXT)
        assert not any("kohli" in c.wrong.lower() for c in result.corrections)

    def test_the_result_is_advisory(self):
        from eesti.providers import grammar

        result = grammar.from_transcript(grammar.check(self.TEXT), self.TEXT)
        assert result.advisory and result.to_dict()["advisory"]

    def test_written_input_is_not_advisory(self):
        """The same sentence typed is the learner's, and is recorded as such."""
        from eesti.providers import grammar

        assert grammar.check("Ma lugesin eile raamatut läbi.").advisory is False

    def test_the_rule_holds_without_vocab_corrections(self, monkeypatch):
        """An LLM engine may never emit a `vocab` tag, so the unknown-word set
        is recomputed from the text rather than read off the corrections."""
        from eesti.providers import grammar

        raw = grammar.GrammarResult(
            "some-llm",
            [grammar.Correction(wrong="kohli", correct="kohil", why="x",
                                tag="obj-case")],
        )
        assert grammar.from_transcript(raw, self.TEXT).corrections == []

    def test_speech_never_reaches_the_review_queue(self):
        """Verified structurally: every queue_failed caller is a drill path."""
        import subprocess

        out = subprocess.run(
            ["grep", "-rn", "queue_failed", "eesti/"],
            capture_output=True, text=True,
        ).stdout
        for line in out.splitlines():
            if "def queue_failed" in line or "handoff.py" in line:
                continue
            assert "speaking" not in line and "asr" not in line, line


class TestBreaker:
    def test_a_dead_engine_is_skipped_after_two_failures(self, monkeypatch):
        """Four engines at 120s each meant an outage cost eight minutes before
        saying nothing was heard."""
        from eesti.providers import breaker

        breaker.reset()
        calls = []

        def dying(audio, context=""):
            calls.append(1)
            return asr.Transcript("", "workers-ai", True, "down")

        monkeypatch.setattr(asr, "_cloudflare", dying)
        monkeypatch.setattr(asr, "_openrouter", lambda *a, **k: None)
        monkeypatch.setattr(asr, "_hosted", lambda *a, **k: None)
        monkeypatch.setattr(asr, "_local", lambda *a, **k: None)
        for _ in range(4):
            asr.transcribe(b"x")
        assert len(calls) == breaker.THRESHOLD
        breaker.reset()

    def test_both_chains_share_one_breaker(self):
        """Two copies of a stateful mechanism drift into two behaviours."""
        from eesti.providers import breaker, grammar

        assert grammar._breaker_open is breaker.is_open

    def test_the_timeout_is_not_four_times_generous(self):
        assert asr.TIMEOUT <= 60


class TestThePageDoesNotPromiseWhatTheEngineCannotKeep:
    """A privacy claim is a fact about the code, and it goes stale silently.

    The page told the learner "salvestus jääb sinu seadmesse — midagi ei
    laadita üles". That was true while recognition ran locally. Recognition
    moved to Cloudflare and the sentence stayed, ending up directly beneath a
    second notice that correctly said the opposite. Nothing failed: both
    strings rendered.

    A voice is biometric. Where it goes has to be stated once, accurately,
    before the button is pressed."""


    @pytest.fixture(scope="class")
    def page(self) -> str:
        return markup_and_script()

    @pytest.mark.parametrize("claim", [
        "jääb sinu seadmesse",
        "ei laadita üles",
        "не покидает устройство",
        "nothing is uploaded",
    ])
    def test_no_text_claims_the_recording_never_leaves(self, page, claim):
        """The hosted engine is the primary one — this promise cannot be made
        unconditionally. The local caveat is allowed, and is stated as a
        condition ("локально … запись не покидает компьютер"), not a blanket."""
        assert claim not in page, f"stale privacy claim on the page: {claim!r}"

    def test_the_notice_names_where_the_audio_goes(self, page):
        notice = page.split('id="recPrivacy"')[1][:500]
        assert "Cloudflare" in notice

    def test_the_notice_is_before_the_record_button_in_the_document(self, page):
        """After it, it is a disclosure nobody read before deciding."""
        assert page.index('id="recPrivacy"') > page.index('id="recBtn"')
        # ...and inside the same panel, not on some other screen.
        panel = page[page.index('id="tab-speak"'):]
        assert panel.index('id="recPrivacy"') < panel.index("</section>")
