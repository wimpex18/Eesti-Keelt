"""Which AI the app can reach, and the two lanes that could never answer.

An audit on 2026-08-20 found three things wrong at once, all of the same shape:
a provider that existed and was never called, a model that was pinned after its
own eval failed it, and a service configured in `config.py` with no caller
anywhere in the codebase.

  * **`huggingface` was in `PROVIDERS` and not in `LLM_PREFERENCE`.** The chain
    could not reach it. It also pointed at `router.huggingface.co`, which serves
    132 models and not one Estonian one — every Estonian model, EstLLM included,
    has an empty `inferenceProviderMapping`. So the lane could not have answered
    even if the chain had tried it.
  * **OpenRouter was pinned to a model this project's eval scored 0.50/0.50**,
    failing in the harmful direction: flagging correct Estonian.
  * **`TARTUNLP_TRANSLATE` had no caller.** A free, keyless, Estonian-trained
    service that has answered every probe since the first research round, sitting
    unused next to a grammar endpoint on the same host that has answered none.
"""

from __future__ import annotations

import pytest

from eesti.providers import grammar, llm


class TestEveryProviderIsReachable:
    def test_nothing_is_defined_and_never_tried(self):
        """The `huggingface` bug, as an assertion. A provider in `PROVIDERS`
        that is absent from `LLM_PREFERENCE` is dead weight nobody notices,
        because nothing fails — the chain simply walks past a lane that is not
        in it."""
        orphans = sorted(set(llm.PROVIDERS) - set(grammar.LLM_PREFERENCE))
        assert not orphans, f"defined but never tried: {orphans}"

    def test_nothing_is_tried_that_does_not_exist(self):
        """The other direction: a typo in the preference tuple would build a
        chain entry that raises rather than degrades."""
        unknown = sorted(set(grammar.LLM_PREFERENCE) - set(llm.PROVIDERS))
        assert not unknown, f"named in the chain but undefined: {unknown}"

    def test_the_chain_ends_somewhere_that_always_answers(self):
        names = [p.name for p in grammar.build_chain()]
        assert names[-1] == "vabamorf-offline"


class TestTheSelfHostedLane:
    """EstLLM cannot be reached through anyone's API — probed 2026-08-20, every
    Estonian model has an empty provider mapping. It can be reached on a machine
    you own, and GGUF builds exist, so the lane points at an OpenAI-compatible
    server instead of at a host that does not serve it."""

    def test_it_is_off_unless_a_server_is_named(self, monkeypatch):
        monkeypatch.delenv("LOCAL_LLM_URL", raising=False)
        assert llm.PROVIDERS["local"].available is False

    def test_naming_a_server_turns_it_on(self, monkeypatch):
        monkeypatch.setenv("LOCAL_LLM_URL", "http://mac-mini.local:11434/v1")
        assert llm.PROVIDERS["local"].available is True

    def test_it_needs_no_key(self, monkeypatch):
        """A local server has nothing to authenticate. Treating "no key" as
        "unavailable" is what made a keyless lane permanently invisible."""
        monkeypatch.setenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
        assert llm.PROVIDERS["local"].key_env == ""
        assert llm.PROVIDERS["local"].api_key is None
        assert llm.PROVIDERS["local"].available is True

    def test_the_url_is_resolved_at_call_time(self, monkeypatch):
        """Set after import must still take effect — the same rule this project
        follows for database paths, for the same reason."""
        monkeypatch.setenv("LOCAL_LLM_URL", "http://elsewhere:8080/v1/")
        assert llm._base_url(llm.PROVIDERS["local"]) == "http://elsewhere:8080/v1"

    def test_it_is_tried_before_the_metered_ones(self, monkeypatch):
        """Not a guess about quality: it is the only lane running a model built
        for Estonian, and it is free, private and unmetered."""
        order = list(grammar.LLM_PREFERENCE)
        assert order.index("local") < order.index("openrouter")

    def test_the_default_model_is_a_gguf_anyone_can_pull(self):
        model = llm.PROVIDERS["local"].default_model
        assert "EstLLM" in model and "GGUF" in model


class TestThePinnedModelIsTheOneTheResearchChose:
    def test_the_failed_model_is_no_longer_pinned(self):
        """0.50 recall / 0.50 precision, and wrong in the harmful direction:
        it flagged `Ma ostsin uue auto` and `Ma sõin suppi`, both correct."""
        assert "nemotron-3-super" not in llm.PROVIDERS["openrouter"].default_model

    def test_the_app_and_the_eval_agree_on_which_model_to_measure(self):
        """They disagreed: the workflow defaulted to Gemma while the app ran
        Nemotron, so the number in CI was never about the model in production."""
        from pathlib import Path

        workflow = (Path(__file__).resolve().parent.parent
                    / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
        assert llm.PROVIDERS["openrouter"].default_model in workflow


class TestTheEvalGateCanActuallyRun:
    @staticmethod
    def _workflow() -> str:
        from pathlib import Path

        return (Path(__file__).resolve().parent.parent
                / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")

    def test_it_no_longer_fires_on_every_provider_change(self):
        """16 runs in one day is ~288 requests against a 50/day free tier. The
        eval then measured nothing, and a gate that cannot run is not a gate."""
        head = self._workflow().split("jobs:", 1)[0]
        assert "pull_request:" not in head

    def test_it_still_runs_on_a_schedule_and_on_demand(self):
        head = self._workflow().split("jobs:", 1)[0]
        assert "schedule:" in head and "workflow_dispatch:" in head


class TestTheModelIsSwitchableWithoutADeploy:
    """Trying a different model was a code change and a redeploy. That is a high
    price for an experiment whose whole point is that the answer is unknown —
    and this project ran the wrong model in production for weeks precisely
    because switching it meant editing a constant."""

    def test_the_default_is_used_when_nothing_is_set(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
        p = llm.PROVIDERS["openrouter"]
        assert p.model == p.default_model

    def test_an_override_wins(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_MODEL", "some/other:free")
        assert llm.PROVIDERS["openrouter"].model == "some/other:free"

    def test_a_dash_in_the_name_becomes_an_underscore(self, monkeypatch):
        """`workers-ai` cannot be an environment variable name."""
        monkeypatch.setenv("WORKERS_AI_MODEL", "@cf/meta/llama-3.1-8b-instruct")
        assert llm.PROVIDERS["workers-ai"].model == "@cf/meta/llama-3.1-8b-instruct"

    def test_the_local_lane_pairs_with_its_url_variable(self, monkeypatch):
        """`LOCAL_LLM_MODEL` beside `LOCAL_LLM_URL`, rather than a second naming
        convention sitting next to the first."""
        monkeypatch.setenv("LOCAL_LLM_MODEL", "hf.co/x/y:Q4_K_M")
        assert llm.PROVIDERS["local"].model == "hf.co/x/y:Q4_K_M"

    def test_an_empty_override_falls_back_rather_than_calling_nothing(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_MODEL", "")
        p = llm.PROVIDERS["openrouter"]
        assert p.model == p.default_model


class TestTheKeylessLaneSendsNoAuthorisation:
    """`Bearer None` is a header that happens to work only because Ollama
    ignores it. A local server has nothing to authenticate."""

    def test_a_keyless_provider_sends_no_authorization_header(self, monkeypatch):
        monkeypatch.setenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
        sent = {}

        class Fake:
            def read(self):
                import json as j
                return j.dumps({"choices": [{"message": {"content": "{}"}}]}).encode()
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def capture(request, *a, **k):
            sent["headers"] = dict(request.headers)
            return Fake()

        monkeypatch.setattr(llm.urllib.request, "urlopen", capture)
        monkeypatch.setattr(llm, "_throttle", lambda: None)
        llm.complete("local", "sys", "user")
        assert not any(k.lower() == "authorization" for k in sent["headers"])

    def test_a_keyed_provider_still_sends_one(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        sent = {}

        class Fake:
            def read(self):
                import json as j
                return j.dumps({"choices": [{"message": {"content": "{}"}}]}).encode()
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def capture(request, *a, **k):
            sent["headers"] = dict(request.headers)
            return Fake()

        monkeypatch.setattr(llm.urllib.request, "urlopen", capture)
        monkeypatch.setattr(llm, "_throttle", lambda: None)
        llm.complete("openrouter", "sys", "user")
        assert any(k.lower() == "authorization" for k in sent["headers"])

    def test_an_unconfigured_keyless_lane_says_what_to_set(self, monkeypatch):
        monkeypatch.delenv("LOCAL_LLM_URL", raising=False)
        with pytest.raises(RuntimeError, match="LOCAL_LLM_URL"):
            llm.complete("local", "sys", "user")


class TestTheModelChoiceIsDefensibleWithoutAnEval:
    """Picked on evidence, because the eval needs a key this repo must never
    hold. The axis that decided it is *active* parameters: the Estonian
    benchmark work frames weak Estonian as either less training data or less
    model capacity dedicated to the language."""

    def test_it_is_not_the_model_that_was_measured_failing(self):
        assert "nemotron-3-super" not in llm.PROVIDERS["openrouter"].default_model

    def test_it_is_not_the_small_active_moe_that_replaced_it(self):
        """`gemma-4-26b-a4b` is 3.8B active — fewer than the 12B-active model
        that scored 0.50/0.50, which is the wrong direction entirely."""
        assert "a4b" not in llm.PROVIDERS["openrouter"].default_model

    def test_the_workflow_offers_the_same_model_first(self):
        from pathlib import Path

        workflow = (Path(__file__).resolve().parent.parent
                    / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
        assert llm.PROVIDERS["openrouter"].default_model in workflow
