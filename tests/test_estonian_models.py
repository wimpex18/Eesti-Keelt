"""The two Estonian-adapted models, and the lanes that reach them.

Both arrived the same way: a claim about somebody else's infrastructure went
stale in the direction that hides an option. `docs/local-llm.md` recorded on
2026-08-20 that nobody hosted any Estonian model, which was true, and three
weeks later `tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125` was served by
featherless-ai and TalTech had published an Estonian Voxtral. Neither is
adopted on the strength of being new — what is asserted here is that the lanes
exist, are reachable, and are ordered for stated reasons.

What these tests deliberately do **not** assert is that either model is any
good. That needs a key this repository must never hold and a machine this
container is not, and `cli eval --provider huggingface` is the command that
settles it.
"""

from __future__ import annotations

import subprocess

import pytest

from eesti.providers import asr, grammar, llm


class TestTheHostedEstLLMLaneExists:
    """It existed once, could never answer, and was deleted. It is back because
    the measurement changed."""

    def test_the_provider_is_registered(self):
        assert "huggingface" in llm.PROVIDERS

    def test_it_pins_the_estonian_model(self):
        assert llm.PROVIDERS["huggingface"].default_model == (
            "tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125")

    def test_it_reuses_the_token_this_deployment_already_knows(self):
        """`HF_TOKEN` is read by the ASR chain for hosted Whisper, so turning
        this on adds a lane rather than a secret."""
        assert llm.PROVIDERS["huggingface"].key_env == "HF_TOKEN"
        assert "HF_TOKEN" in __import__("eesti.env", fromlist=["x"]).KNOWN_KEYS

    def test_it_speaks_the_shape_this_client_already_sends(self):
        """The router is OpenAI-compatible, which is the whole reason one
        client covers every provider here."""
        assert llm.PROVIDERS["huggingface"].base_url.endswith("/v1")

    def test_a_missing_token_is_simply_unavailable(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        assert llm.PROVIDERS["huggingface"].available is False

    def test_the_model_is_overridable_from_the_environment(self, monkeypatch):
        """The 70B exists and nobody hosts it yet; the day somebody does, this
        must not be a code change and a redeploy."""
        monkeypatch.setenv("HUGGINGFACE_MODEL", "tartuNLP/something-else")
        assert llm.PROVIDERS["huggingface"].model == "tartuNLP/something-else"


class TestItIsActuallyInTheChain:
    """The bug this lane is famous for: defined in `PROVIDERS`, absent from
    `LLM_PREFERENCE`, tried by nothing, noticed by nobody."""

    def test_the_grammar_chain_includes_it(self):
        assert "huggingface" in grammar.LLM_PREFERENCE

    def test_it_is_tried_before_the_general_purpose_models(self):
        """Same argument as `local`, not a new one: it runs the same
        Estonian-adapted model, on hardware somebody else owns."""
        order = list(grammar.LLM_PREFERENCE)
        assert order.index("huggingface") < order.index("openrouter")
        assert order.index("local") < order.index("huggingface")

    def test_the_built_chain_really_contains_that_provider(self):
        """Through `build_chain`, not the tuple — the tuple could be right and
        the construction still drop it."""
        assert "llm:huggingface" in [p.name for p in grammar.build_chain()]

    def test_the_eval_can_score_every_lane_the_client_knows(self):
        """`--provider` was a hand-written tuple that offered `huggingface`
        when no such provider existed and omitted `local`, so the one
        Estonian-adapted lane was the one the eval could not measure."""
        from eesti.cli.build import _providers

        assert set(_providers()) == set(llm.PROVIDERS)
        assert {"local", "huggingface"} <= set(_providers())

    def test_the_eval_command_accepts_it(self):
        """End to end through argparse, because `choices` is where this broke."""
        done = subprocess.run(
            ["python", "-m", "eesti.cli", "eval", "--help"],
            capture_output=True, text=True)
        assert done.returncode == 0, done.stderr[-500:]
        assert "huggingface" in done.stdout and "local" in done.stdout


class TestTheVoxtralLane:
    def test_the_engine_is_in_the_chain(self):
        """Read from `transcribe`'s own attempt list, so a lane that is defined
        and never tried fails here — the exact shape of the EstLLM bug above."""
        import inspect

        source = inspect.getsource(asr.transcribe)
        assert '"voxtral"' in source

    def test_it_is_reported_as_an_engine(self):
        assert "voxtral" in asr.available()

    def test_all_three_paths_are_required(self, monkeypatch, tmp_path):
        """The `mmproj` file is what lets the model hear. Without it the binary
        still loads and still answers, about audio it never received."""
        model = tmp_path / "voxtral.gguf"
        model.write_bytes(b"")
        monkeypatch.setenv("VOXTRAL_BIN", "/bin/true")
        monkeypatch.setenv("VOXTRAL_MODEL_PATH", str(model))
        monkeypatch.delenv("VOXTRAL_MMPROJ", raising=False)
        assert asr._voxtral_paths() == (None, None, None)

    def test_a_path_that_is_not_there_does_not_count(self, monkeypatch, tmp_path):
        monkeypatch.setenv("VOXTRAL_BIN", "/bin/true")
        monkeypatch.setenv("VOXTRAL_MODEL_PATH", str(tmp_path / "never-pulled.gguf"))
        monkeypatch.setenv("VOXTRAL_MMPROJ", str(tmp_path / "nor-this.gguf"))
        assert asr._voxtral_paths() == (None, None, None)

    def test_an_unconfigured_engine_is_not_a_failure(self, monkeypatch):
        """`None` means "not set up" and `Transcript(degraded=True)` means
        "tried and failed". Confusing them trips a breaker on a machine that
        simply never had the model."""
        monkeypatch.delenv("VOXTRAL_BIN", raising=False)
        monkeypatch.delenv("VOXTRAL_MODEL_PATH", raising=False)
        monkeypatch.delenv("VOXTRAL_MMPROJ", raising=False)
        assert asr._voxtral(b"nothing") is None


class TestVoxtralIsAskedTheRightQuestion:
    @pytest.fixture
    def configured(self, monkeypatch, tmp_path):
        """A fake binary that records its argv and prints a transcript."""
        record = tmp_path / "argv.txt"
        fake = tmp_path / "llama-mtmd-cli"
        fake.write_text(
            "#!/bin/sh\n"
            f'printf "%s\\n" "$@" > {record}\n'
            'echo "diagnostics" >&2\n'
            'echo "  Ma elan Tallinnas.  "\n',
            encoding="utf-8")
        fake.chmod(0o755)
        for name in ("m.gguf", "mm.gguf"):
            (tmp_path / name).write_bytes(b"")
        monkeypatch.setenv("VOXTRAL_BIN", str(fake))
        monkeypatch.setenv("VOXTRAL_MODEL_PATH", str(tmp_path / "m.gguf"))
        monkeypatch.setenv("VOXTRAL_MMPROJ", str(tmp_path / "mm.gguf"))
        return record

    def test_the_transcript_comes_back_trimmed(self, configured):
        result = asr._voxtral(b"audio")
        assert result.text == "Ma elan Tallinnas."
        assert result.degraded is False

    def test_stderr_is_not_mistaken_for_the_answer(self, configured):
        """A multimodal CLI logs on stderr and answers on stdout. Reading the
        wrong stream returns diagnostics as a transcript."""
        assert "diagnostics" not in asr._voxtral(b"audio").text

    def test_it_is_told_to_transcribe(self, configured):
        """It is an audio-*understanding* model: with no instruction it will as
        happily return a summary, a subtitle track or a news story, all of
        which it was trained to produce from the same recording."""
        asr._voxtral(b"audio")
        argv = configured.read_text(encoding="utf-8")
        assert "-p" in argv.split("\n")
        assert "Transcribe" in argv

    def test_the_audio_encoder_is_passed(self, configured):
        asr._voxtral(b"audio")
        assert "--mmproj" in configured.read_text(encoding="utf-8").split("\n")

    def test_a_failing_binary_degrades_rather_than_raises(self, monkeypatch, tmp_path):
        fake = tmp_path / "llama-mtmd-cli"
        fake.write_text("#!/bin/sh\necho 'out of memory' >&2\nexit 1\n", encoding="utf-8")
        fake.chmod(0o755)
        (tmp_path / "m.gguf").write_bytes(b"")
        (tmp_path / "mm.gguf").write_bytes(b"")
        monkeypatch.setenv("VOXTRAL_BIN", str(fake))
        monkeypatch.setenv("VOXTRAL_MODEL_PATH", str(tmp_path / "m.gguf"))
        monkeypatch.setenv("VOXTRAL_MMPROJ", str(tmp_path / "mm.gguf"))
        result = asr._voxtral(b"audio")
        assert result.degraded is True and "out of memory" in result.note


class TestWhatIsRecordedAboutProvenance:
    """Both claims here were stated loosely once, and both change what somebody
    is trusting when they pull these files."""

    def test_the_gguf_builds_are_attributed_to_the_requantiser(self):
        """TalTech published bfloat16 safetensors only. Writing "TalTech's
        Voxtral with GGUF builds" credits the trainer for a conversion somebody
        else did, and whoever pulls them is trusting both."""
        assert asr.VOXTRAL_GGUF.startswith("mradermacher/")
        assert asr.VOXTRAL_MODEL.startswith("TalTechNLP/")

    def test_the_incumbent_estonian_model_is_still_named(self):
        assert asr.ESTONIAN_MODEL == "TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604"
