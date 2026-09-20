"""The LLM lanes, the eval workflow that scores them, and the local ASR engines."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from eesti.providers import asr, grammar, llm

ROOT = Path(__file__).resolve().parents[1]


def _eval_workflow() -> dict:
    # PyYAML reads `on:` as the boolean True (YAML 1.1).
    return yaml.safe_load((ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8"))


def _capture_requests(monkeypatch, content="{}"):
    """Replace urlopen; return the list of requests sent."""
    sent = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": content}}], "data": []}).encode()

    def fake(req, timeout=None):
        sent.append(req)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake)
    monkeypatch.setattr(llm, "_throttle", lambda: None)
    return sent


class TestTheChain:
    def test_every_lane_is_tried_and_every_tried_lane_exists(self):
        assert set(llm.PROVIDERS) == set(grammar.LLM_PREFERENCE)

    def test_the_chain_ends_somewhere_that_always_answers(self):
        assert [p.name for p in grammar.build_chain()][-1] == "vabamorf-offline"

    def test_every_lane_is_free(self):
        for name, provider in llm.PROVIDERS.items():
            assert provider.free_note, name
            assert not provider.free_note.lower().startswith("paid"), name

    def test_the_estonian_local_lane_is_tried_first(self):
        assert grammar.LLM_PREFERENCE[0] == "local"


class TestTheLocalLane:
    def test_it_is_off_unless_a_server_is_named(self, monkeypatch):
        monkeypatch.delenv("LOCAL_LLM_URL", raising=False)
        assert llm.PROVIDERS["local"].available is False

    def test_naming_a_server_turns_it_on_without_a_key(self, monkeypatch):
        monkeypatch.setenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
        local = llm.PROVIDERS["local"]
        assert local.key_env == "" and local.api_key is None and local.available

    def test_the_url_is_resolved_at_call_time(self, monkeypatch):
        monkeypatch.setenv("LOCAL_LLM_URL", "http://elsewhere:8080/v1/")
        assert llm._base_url(llm.PROVIDERS["local"]) == "http://elsewhere:8080/v1"

    def test_the_default_model_is_the_estonian_gguf(self):
        model = llm.PROVIDERS["local"].default_model
        assert "EstLLM" in model and "GGUF" in model

    def test_an_unconfigured_keyless_lane_says_what_to_set(self, monkeypatch):
        monkeypatch.delenv("LOCAL_LLM_URL", raising=False)
        with pytest.raises(RuntimeError, match="LOCAL_LLM_URL"):
            llm.complete("local", "sys", "user")


class TestModelOverrides:
    def test_the_default_is_used_when_nothing_is_set(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
        p = llm.PROVIDERS["openrouter"]
        assert p.model == p.default_model

    def test_an_override_wins(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_MODEL", "some/other:free")
        assert llm.PROVIDERS["openrouter"].model == "some/other:free"

    def test_a_dash_becomes_an_underscore(self, monkeypatch):
        monkeypatch.setenv("WORKERS_AI_MODEL", "@cf/meta/llama-3.1-8b-instruct")
        assert llm.PROVIDERS["workers-ai"].model == "@cf/meta/llama-3.1-8b-instruct"

    def test_the_local_lane_reads_local_llm_model(self, monkeypatch):
        monkeypatch.setenv("LOCAL_LLM_MODEL", "hf.co/x/y:Q4_K_M")
        assert llm.PROVIDERS["local"].model == "hf.co/x/y:Q4_K_M"

    def test_an_empty_override_falls_back(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_MODEL", "")
        p = llm.PROVIDERS["openrouter"]
        assert p.model == p.default_model


class TestTheRequest:
    def test_a_keyless_lane_sends_no_authorization(self, monkeypatch):
        monkeypatch.setenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
        sent = _capture_requests(monkeypatch)
        llm.complete("local", "sys", "user")
        assert not any(k.lower() == "authorization" for k in dict(sent[0].headers))

    def test_a_keyed_lane_sends_one(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        sent = _capture_requests(monkeypatch)
        llm.complete("openrouter", "sys", "user")
        assert any(k.lower() == "authorization" for k in dict(sent[0].headers))

    def test_completions_and_catalogues_send_the_apps_user_agent(self, monkeypatch):
        from eesti.net import UA

        monkeypatch.setenv("NVIDIA_API_KEY", "test-key-not-real")
        sent = _capture_requests(monkeypatch)
        llm.list_models("nvidia")
        llm.complete("nvidia", "s", "u")
        assert [r.get_header("User-agent") for r in sent] == [UA, UA]

    def test_json_mode_is_sent_only_where_the_lane_supports_it(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        monkeypatch.setenv("NVIDIA_API_KEY", "k")
        sent = _capture_requests(monkeypatch)
        llm.complete("openrouter", "sys", "user")
        llm.complete("nvidia", "sys", "user")
        with_mode, without = (json.loads(r.data) for r in sent)
        assert with_mode["response_format"] == {"type": "json_object"}
        assert "response_format" not in without

    def test_without_json_mode_the_prompt_and_parser_still_cope(self):
        from eesti.evals.gec import SYSTEM

        assert "ONLY valid JSON" in SYSTEM
        assert llm.parse_json('```json\n{"corrections": []}\n```') == {"corrections": []}

    def test_an_empty_reply_is_named(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")

        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self):
                return json.dumps({"choices": [{"message": {"content": None},
                                                "finish_reason": "length"}]}).encode()

        monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: Response())
        monkeypatch.setattr(llm, "_throttle", lambda: None)
        with pytest.raises(llm.EmptyReply) as caught:
            llm.complete("openrouter", "s", "u")
        assert grammar.why_failed(caught.value) == "empty reply (length)"


class TestTheEvalWorkflow:
    #: No runner has a server on LOCAL_LLM_URL.
    NOT_IN_CI = {"local"}
    SENTINEL = "(provider default)"

    @property
    def inputs(self) -> dict:
        return _eval_workflow()[True]["workflow_dispatch"]["inputs"]

    @staticmethod
    def _score_step() -> str:
        steps = _eval_workflow()["jobs"]["eval"]["steps"]
        return next(s for s in steps if s.get("id") == "score")["run"]

    def test_the_provider_menu_matches_the_client(self):
        from eesti.evals.gec import NON_LLM

        assert set(self.inputs["provider"]["options"]) == (
            set(llm.PROVIDERS) - self.NOT_IN_CI) | set(NON_LLM)

    def test_every_provider_option_has_its_key_plumbed(self):
        env = _eval_workflow()["jobs"]["eval"]["env"]
        for name in self.inputs["provider"]["options"]:
            if name not in llm.PROVIDERS:
                continue  # a keyless non-LLM lane (`evals.gec.NON_LLM`)
            key = llm.PROVIDERS[name].key_env
            assert not key or key in env, name

    def test_every_selectable_model_is_free(self):
        pinned = {p.default_model for p in llm.PROVIDERS.values()}
        for option in self.inputs["model"]["options"]:
            assert option == self.SENTINEL or option.endswith(":free") or option in pinned, option

    def test_the_default_model_is_free_and_pinned(self):
        default = self.inputs["model"]["default"]
        assert default.endswith(":free") and default == llm.PROVIDERS["openrouter"].default_model

    def test_the_sentinel_passes_no_model(self):
        assert self.SENTINEL in self.inputs["model"]["options"]
        assert self.SENTINEL in self._score_step()

    def test_the_key_check_asks_about_the_selected_provider(self):
        step = self._score_step()
        assert "PROVIDERS.get('$PROVIDER')" in step and "lane.available" in step

    def test_it_runs_weekly_and_on_demand_only(self):
        on = _eval_workflow()[True]
        assert set(on) == {"workflow_dispatch", "schedule"}


class TestVoxtral:
    def test_the_engine_is_in_the_chain_and_reported(self):
        assert "voxtral" in [name for name, _ in asr.engines(b"x")]
        assert "voxtral" in asr.available()

    def test_all_three_paths_must_exist(self, monkeypatch, tmp_path):
        model = tmp_path / "voxtral.gguf"
        model.write_bytes(b"")
        monkeypatch.setenv("VOXTRAL_BIN", "/bin/true")
        monkeypatch.setenv("VOXTRAL_MODEL_PATH", str(model))
        monkeypatch.delenv("VOXTRAL_MMPROJ", raising=False)
        assert asr._voxtral_paths() == (None, None, None)
        monkeypatch.setenv("VOXTRAL_MMPROJ", str(tmp_path / "missing.gguf"))
        assert asr._voxtral_paths() == (None, None, None)

    def test_an_unconfigured_engine_is_not_a_failure(self, monkeypatch):
        for name in ("VOXTRAL_BIN", "VOXTRAL_MODEL_PATH", "VOXTRAL_MMPROJ"):
            monkeypatch.delenv(name, raising=False)
        assert asr._voxtral(b"nothing") is None

    @pytest.fixture
    def fake_binary(self, monkeypatch, tmp_path):
        def make(script: str):
            fake = tmp_path / "llama-mtmd-cli"
            fake.write_text("#!/bin/sh\n" + script, encoding="utf-8")
            fake.chmod(0o755)
            for name in ("m.gguf", "mm.gguf"):
                (tmp_path / name).write_bytes(b"")
            monkeypatch.setenv("VOXTRAL_BIN", str(fake))
            monkeypatch.setenv("VOXTRAL_MODEL_PATH", str(tmp_path / "m.gguf"))
            monkeypatch.setenv("VOXTRAL_MMPROJ", str(tmp_path / "mm.gguf"))
            return tmp_path / "argv.txt"
        return make

    def test_it_is_asked_to_transcribe_and_answers_on_stdout(self, fake_binary):
        record = fake_binary(
            'printf "%s\\n" "$@" > "$(dirname "$0")/argv.txt"\n'
            'echo "diagnostics" >&2\necho "  Ma elan Tallinnas.  "\n')
        result = asr._voxtral(b"audio")
        argv = record.read_text(encoding="utf-8").split("\n")
        assert result.text == "Ma elan Tallinnas." and not result.degraded
        assert "-p" in argv and "--mmproj" in argv
        assert any("Transcribe" in a for a in argv)

    def test_a_failing_binary_degrades_rather_than_raises(self, fake_binary):
        fake_binary("echo 'out of memory' >&2\nexit 1\n")
        result = asr._voxtral(b"audio")
        assert result.degraded is True and "out of memory" in result.note


class TestTartuNLPIsEvaluated:
    """TartuNLP answers first in the grammar chain, so the eval must be able to
    score it, through the same client the app uses.
    """

    def test_the_eval_scores_tartunlp_through_the_app_client(self, monkeypatch):
        from eesti.evals import gec
        from eesti.providers.grammar import Correction, GrammarResult, TartuNLPGrammar

        def fake_check(self, text):
            flagged = [c for c in gec.CASES if c.wrong and c.sentence == text]
            return GrammarResult("tartunlp", [
                Correction(wrong=c.wrong, correct=c.correct or "", why="")
                for c in flagged])

        monkeypatch.setattr(TartuNLPGrammar, "check", fake_check)
        score = gec.run("tartunlp", verbose=False)
        assert score["valid"]
        assert score["recall"] == 1.0 and score["precision"] == 1.0

    def test_the_cli_offers_it(self):
        import argparse

        from eesti.cli import build

        parser = argparse.ArgumentParser()
        build.register(parser.add_subparsers())
        args = parser.parse_args(["eval", "--provider", "tartunlp"])
        assert args.provider == "tartunlp"
