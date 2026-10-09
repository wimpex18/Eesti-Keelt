"""The Claude lane (DEV-38): Anthropic's Messages API through the official SDK.

What a learner would notice if these broke: a refused or empty answer shown as
an explanation; a request rejected for a sampling setting Haiku 5.5 does not
take; one learner's explanation waiting behind another's for 3.5 seconds; a
prompt long enough to double the price; the lane answering before its eval.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from eesti.providers import claude, llm


class _Client:
    """Stands in for `anthropic.Anthropic`: records the request, returns a reply."""

    def __init__(self, reply, sent):
        self._reply, self._sent = reply, sent
        self.messages = self

    def create(self, **params):
        self._sent.append(params)
        return self._reply


def _reply(*blocks, stop="end_turn", category=None):
    return SimpleNamespace(
        content=list(blocks), stop_reason=stop,
        stop_details=SimpleNamespace(category=category) if category else None,
        usage=SimpleNamespace(input_tokens=120, output_tokens=40))


def _text(t):
    return SimpleNamespace(type="text", text=t)


@pytest.fixture
def lane(monkeypatch):
    sent: list[dict] = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    def install(reply):
        monkeypatch.setattr(claude, "_client", lambda timeout: _Client(reply, sent))
        return sent
    return install


def test_the_request_is_one_haiku_5_5_accepts(lane):
    sent = lane(_reply(_text('{"corrections": []}')))
    claude.complete("süsteem", "Ma ostsin leib.", schema={"type": "object"})
    params = sent[0]
    assert params["model"] == "claude-haiku-5-5"
    # Haiku 5.5 rejects non-default sampling and prefill: none is sent.
    assert not {"temperature", "top_p", "top_k"} & set(params)
    assert params["messages"][-1]["role"] == "user"
    assert params["output_config"]["effort"] in ("low", "medium", "high")
    assert params["output_config"]["format"]["type"] == "json_schema"


def test_thinking_blocks_are_skipped_and_text_is_read(lane):
    lane(_reply(SimpleNamespace(type="thinking", thinking=""), _text('{"a": 1}')))
    assert claude.complete("s", "u") == '{"a": 1}'


def test_a_refusal_is_a_failed_lane_not_an_answer(lane):
    lane(_reply(stop="refusal", category="general_harms"))
    with pytest.raises(claude.Refused):
        claude.complete("s", "u")


def test_an_empty_reply_is_a_failure(lane):
    lane(_reply(stop="max_tokens"))
    with pytest.raises(llm.EmptyReply):
        claude.complete("s", "u")


def test_a_prompt_past_the_price_threshold_is_refused_before_sending(lane):
    sent = lane(_reply(_text("{}")))
    with pytest.raises(ValueError, match="long"):
        claude.complete("s", "x" * (claude.MAX_PROMPT_CHARS + 1))
    assert sent == []


def test_the_chain_reaches_it_through_complete(lane):
    sent = lane(_reply(_text('{"corrections": []}')))
    assert llm.complete("anthropic", "s", "u", attempts=1) == '{"corrections": []}'
    assert sent


def test_without_a_key_the_lane_is_not_available(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not llm.PROVIDERS["anthropic"].available


def test_learners_are_not_paced_only_evaluations_are(lane, monkeypatch):
    """The 3.5 s pause protects a free tier during an eval; a learner's tutor
    call must not wait behind another learner's."""
    lane(_reply(_text("{}")))
    slept: list[float] = []
    monkeypatch.setattr(llm.time, "sleep", slept.append)
    monkeypatch.setattr(llm, "_last_call", llm.time.monotonic())
    llm.complete("anthropic", "s", "u", attempts=1)
    llm.complete("anthropic", "s", "u", attempts=1)
    assert slept == []


def test_it_does_not_answer_learners_before_its_eval():
    """ADR-0008: the lane joins the chain only after the agreed eval passes."""
    from eesti.providers.grammar import LLM_PREFERENCE

    assert "anthropic" not in LLM_PREFERENCE


def test_the_grammar_check_asks_for_its_own_shape(lane):
    """Structured output holds the corrections to the schema the parser reads."""
    from eesti.providers.grammar import CORRECTIONS_SCHEMA, LLMGrammar

    sent = lane(_reply(_text('{"corrections": []}')))
    LLMGrammar("anthropic").check("Ma ostsin leiba.")
    assert sent[0]["output_config"]["format"]["schema"] == CORRECTIONS_SCHEMA


def test_the_ledger_says_what_leaves_and_how_long_it_stays():
    from eesti.licences import ENGINES

    entry = next(s for s in ENGINES if s.id == "anthropic")
    assert entry.data_leaves == "text"
    assert "30" in entry.retention
