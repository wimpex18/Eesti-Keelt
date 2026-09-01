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


def _script(step: dict) -> str:
    """A workflow step's shell, without its comments.

    Both assertions below search a step's `run:` for a construct, and both were
    written to pass against a comment. The comment above the key check quotes
    the old `cli keys | grep` so the reader knows what changed, and the comment
    above the sentinel names `(provider default)` — so a naive search finds the
    prose, reports the construct present, and stays green when the code that
    was supposed to contain it is deleted. Both of those actually happened.
    """
    return "\n".join(line for line in step["run"].splitlines()
                     if not line.lstrip().startswith("#"))


class TestTheEvalCanActuallySelectTheEstonianLane:
    """`eval.yml` is the only place a key is ever spent, so a lane it cannot
    select is a lane that can never produce a number.

    Its `options:` list is hand-maintained because Actions YAML cannot read
    `llm.PROVIDERS` — which makes it the third instance of this repository's
    most-repeated bug, after `huggingface` sitting in `PROVIDERS` and in no
    chain, and `cli/build.py` offering a `huggingface` that did not exist while
    omitting `local`. It cannot be derived, so it is checked in both
    directions, the way `api.ROUTERS` is.
    """

    #: The one provider deliberately absent from the workflow, with its reason.
    #: No runner has an Ollama server on `LOCAL_LLM_URL`, and offering a choice
    #: that cannot work is exactly the failure this list guards against.
    NOT_IN_CI = {"local": "needs a server on LOCAL_LLM_URL; no runner has one"}

    @staticmethod
    def _workflow() -> dict:
        import yaml

        from pathlib import Path

        path = (Path(__file__).resolve().parent.parent
                / ".github" / "workflows" / "eval.yml")
        # PyYAML reads the `on:` key as the boolean True (YAML 1.1), which is
        # the kind of detail that makes a hand-written string search look
        # simpler than it is.
        return yaml.safe_load(path.read_text(encoding="utf-8"))[True]

    @classmethod
    def _providers(cls) -> list[str]:
        return cls._workflow()["workflow_dispatch"]["inputs"]["provider"]["options"]

    def test_every_option_is_a_real_provider(self):
        from eesti.providers import llm

        unknown = sorted(set(self._providers()) - set(llm.PROVIDERS))
        assert not unknown, (
            f"{unknown} can be selected in the eval workflow and would raise "
            f"KeyError on the runner")

    def test_every_provider_is_selectable_unless_it_is_excluded(self):
        from eesti.providers import llm

        missing = sorted(set(llm.PROVIDERS) - set(self._providers())
                         - set(self.NOT_IN_CI))
        assert not missing, (
            f"{missing} exist in the client and cannot be scored by the only "
            f"workflow that spends a key — add them, or document the exclusion")

    def test_the_exclusion_is_still_an_exclusion(self):
        """If `local` ever becomes selectable, this dict is stale and the
        reason in it is a lie."""
        for name in self.NOT_IN_CI:
            assert name not in self._providers()

    def test_the_estonian_lane_is_selectable(self):
        assert "huggingface" in self._providers()


class TestTheEstonianLaneCanActuallyBeCalled:
    @staticmethod
    def _job() -> dict:
        import yaml

        from pathlib import Path

        path = (Path(__file__).resolve().parent.parent
                / ".github" / "workflows" / "eval.yml")
        return yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"]["eval"]

    def test_the_token_reaches_the_runner(self):
        """Selectable and keyless is the worst of both: the provider appears in
        the menu and reports "no key configured" with the secret sitting in
        Actions."""
        env = self._job()["env"]
        assert "HF_TOKEN" in env
        assert "secrets.HF_TOKEN" in env["HF_TOKEN"]

    def test_every_provider_option_has_its_key_plumbed(self):
        """Derived from the options rather than listed again here — a second
        hand-written list beside the first is how the first one drifted."""
        import yaml

        from pathlib import Path

        from eesti.providers import llm

        path = (Path(__file__).resolve().parent.parent
                / ".github" / "workflows" / "eval.yml")
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        options = doc[True]["workflow_dispatch"]["inputs"]["provider"]["options"]
        env = doc["jobs"]["eval"]["env"]
        for name in options:
            key = llm.PROVIDERS[name].key_env
            assert not key or key in env, (
                f"{name} can be selected but {key} never reaches the runner")

    def test_the_app_and_the_eval_agree_on_the_estonian_model(self):
        """The same assertion that already guards the OpenRouter pin, and it
        exists because the workflow and the app once disagreed — so the number
        in CI was about neither."""
        from pathlib import Path

        from eesti.providers import llm

        text = (Path(__file__).resolve().parent.parent
                / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
        assert llm.PROVIDERS["huggingface"].default_model in text

    def test_a_model_can_be_left_to_the_provider(self):
        """Every other id in that list is OpenRouter's. Without a sentinel the
        workflow always passed one, so any non-OpenRouter lane was scored
        against an id it has never heard of."""
        import yaml

        from pathlib import Path

        path = (Path(__file__).resolve().parent.parent
                / ".github" / "workflows" / "eval.yml")
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        options = doc[True]["workflow_dispatch"]["inputs"]["model"]["options"]
        assert "(provider default)" in options

        step = next(s for s in doc["jobs"]["eval"]["steps"]
                    if s.get("id") == "score")
        code = _script(step)
        assert "(provider default)" in code, (
            "the sentinel is offered but nothing strips it, so it would be "
            "sent as a literal model id")

    def test_the_key_check_asks_about_the_selected_provider(self):
        """It asked `cli keys | grep ✓` — "is *some* lane configured". With an
        OpenRouter key set and huggingface selected, the eval ran, every call
        failed, and it reported rc=2: rate limit or provider outage. That
        blames a third party for a missing secret."""
        import yaml

        from pathlib import Path

        path = (Path(__file__).resolve().parent.parent
                / ".github" / "workflows" / "eval.yml")
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        step = next(s for s in doc["jobs"]["eval"]["steps"]
                    if s.get("id") == "score")
        code = _script(step)
        assert "PROVIDERS['$PROVIDER'].available" in code
        assert "keys | grep" not in code


class TestAPartialCatalogueDoesNotReadAsABrokenPin:
    """`cli models` ends with PRESENT / ABSENT — fix it, and the eval workflow
    runs it as its "is the pinned id still there" step.

    That verdict comes from the provider's own listing, which for the HF router
    is ~135 warm models rather than an inventory: a model reachable through an
    inference-provider mapping is routable without being in it. EstLLM is
    exactly that, so the honest answer is that this endpoint cannot say.
    """

    def test_the_router_is_marked_as_a_partial_catalogue(self):
        from eesti.cli.build import PARTIAL_CATALOGUE

        assert "huggingface" in PARTIAL_CATALOGUE

    def test_openrouter_is_not(self):
        """The whole reason the verdict exists: OpenRouter withdraws `:free`
        ids silently while the paid one keeps the name."""
        from eesti.cli.build import PARTIAL_CATALOGUE

        assert "openrouter" not in PARTIAL_CATALOGUE

    def test_it_does_not_tell_you_to_fix_a_working_pin(self, capsys, monkeypatch):
        import argparse

        from eesti.cli import build

        monkeypatch.setattr(build, "_providers", lambda: ("huggingface",))
        monkeypatch.setattr("eesti.providers.llm.list_models",
                            lambda provider, timeout=30.0: [{"id": "someone/else"}])
        build.cmd_models(argparse.Namespace(
            provider="huggingface", all=False, limit=5))
        said = capsys.readouterr().out
        assert "ABSENT" not in said
        assert "NOT ANSWERABLE HERE" in said

    def test_a_complete_catalogue_still_gets_a_verdict(self, capsys, monkeypatch):
        import argparse

        from eesti.cli import build
        from eesti.providers import llm

        monkeypatch.setattr("eesti.providers.llm.list_models",
                            lambda provider, timeout=30.0: [{"id": "someone/else"}])
        build.cmd_models(argparse.Namespace(
            provider="openrouter", all=False, limit=5))
        said = capsys.readouterr().out
        assert "ABSENT — fix it" in said
        assert llm.PROVIDERS["openrouter"].default_model in said
