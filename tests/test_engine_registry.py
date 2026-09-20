"""Every engine the app may call is in the registry, with what it costs in
privacy. A lane missing here is a lane nobody vetted.
"""

from __future__ import annotations

import pytest

from eesti.licences import ENGINES, REGISTRY

BY_ID = {s.id: s for s in REGISTRY}


def test_every_grammar_lane_is_registered():
    from eesti.providers.grammar import LLM_PREFERENCE, build_chain

    names = {p.name for p in build_chain()}
    # `vabamorf-offline` is Vabamorf; the LLM lanes carry an `llm:` prefix.
    wanted = {"tartunlp-gec" if n == "tartunlp" else
              "tartunlp-mt" if n == "tartunlp-mt" else
              "vabamorf" if n == "vabamorf-offline" else n
              for n in names}
    wanted = {("local-llm" if n == "llm:local" else n.replace("llm:", ""))
              for n in wanted}
    missing = wanted - set(BY_ID)
    assert not missing, f"unregistered grammar lanes: {sorted(missing)}"
    assert set(LLM_PREFERENCE) - {"local"} <= set(BY_ID)


def test_every_speech_and_translation_engine_is_registered():
    for engine in ("workers-ai", "hf-whisper", "whisper-cpp", "tartunlp-mt"):
        assert engine in BY_ID, engine


@pytest.mark.parametrize("engine", ENGINES, ids=lambda s: s.id)
class TestEachEngineSaysWhatItCosts:
    def test_it_says_what_leaves_the_device(self, engine):
        assert engine.data_leaves in ("none", "text", "audio")

    def test_it_was_checked_and_says_when(self, engine):
        assert engine.verified, f"{engine.id}: no date the terms were checked"

    def test_anything_that_receives_learner_data_says_what_happens_to_it(self, engine):
        """A provider that sees text or audio must have an answer on retention,
        or a stated quota that shows it was read at all."""
        if engine.data_leaves != "none":
            assert engine.retention or engine.quota, engine.id


def test_the_api_serves_the_engines_apart_from_the_licences():
    pytest.importorskip("httpx2")
    from fastapi.testclient import TestClient

    from eesti.app import app

    body = TestClient(app).get("/api/sources").json()
    engines = {e["id"]: e for e in body["engines"]}
    assert engines and set(engines) == {s.id for s in ENGINES}
    assert engines["workers-ai"]["data_leaves"] == "audio"
    assert engines["vabamorf"]["data_leaves"] == "none"


def test_nothing_local_claims_to_send_data_away():
    for engine in ENGINES:
        if engine.id in ("vabamorf", "local-llm", "whisper-cpp", "inflection-et"):
            assert engine.data_leaves == "none", engine.id
