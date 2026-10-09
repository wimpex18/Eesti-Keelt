"""The Claude lane (DEV-38): Anthropic's Messages API through the official SDK.

What a learner would notice if these broke: a refused or empty answer shown as
an explanation; a request rejected for a sampling setting Haiku 5.5 does not
take; one learner's explanation waiting behind another's for 3.5 seconds; a
prompt long enough to cost five times as much; every call paying full price for
the same system prompt; the lane answering before its eval.
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
    """Above 100K tokens every rate is five times higher. Russian takes two
    bytes a letter, so 50,000 letters is already past the bound."""
    sent = lane(_reply(_text("{}")))
    with pytest.raises(ValueError, match="long"):
        claude.complete("s", "я" * 50_000)
    assert sent == []
    claude.complete("s", "x" * 80_000)
    assert len(sent) == 1


def test_the_system_prompt_is_the_cached_prefix(lane):
    """A cache read costs a tenth of fresh input; the learner's text varies, the
    instructions do not, so only the instructions carry the breakpoint."""
    sent = lane(_reply(_text("{}")))
    claude.complete("juhised", "Ma ostsin leib.")
    (block,) = sent[0]["system"]
    assert block["text"] == "juhised"
    assert block["cache_control"] == {"type": "ephemeral"}
    assert isinstance(sent[0]["messages"][0]["content"], str)


def test_an_eval_reports_what_its_tokens_cost(lane, monkeypatch):
    monkeypatch.setattr(claude, "_USAGE", dict.fromkeys(claude._USAGE, 0))
    reply = _reply(_text("{}"))
    reply.usage = SimpleNamespace(input_tokens=1000, output_tokens=2000,
                                  cache_creation_input_tokens=0,
                                  cache_read_input_tokens=1_000_000)
    lane(reply)
    claude.complete("s", "u")
    totals = claude.usage_totals()
    assert totals["calls"] == 1 and totals["cache_read"] == 1_000_000
    # 1M cached at $0.01, 1K fresh at $0.10, 2K out at $0.50 per million.
    assert totals["dollars"] == pytest.approx(0.01 + 0.0001 + 0.001)


def test_effort_is_read_when_the_call_is_made(lane, monkeypatch):
    """The eval sets the level per run; a value bound at import would ignore it."""
    sent = lane(_reply(_text("{}")))
    monkeypatch.setenv("ANTHROPIC_EFFORT", "medium")
    claude.complete("s", "u")
    monkeypatch.delenv("ANTHROPIC_EFFORT")
    claude.complete("s", "u")
    assert [p["output_config"]["effort"] for p in sent] == ["medium", "low"]


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


def test_a_reply_cut_off_by_max_tokens_is_not_an_answer(lane):
    lane(_reply(_text('{"corrections": [{"wrong": "le'), stop="max_tokens"))
    with pytest.raises(llm.EmptyReply):
        claude.complete("s", "u")


def test_a_refusal_does_not_trip_the_breaker(lane):
    """One declined request says nothing about the lane; the breaker's cooldown
    grows to days."""
    from eesti.providers import breaker
    from eesti.providers.grammar import LLMGrammar, check

    lane(_reply(stop="refusal", category="general_harms"))
    breaker.reset()
    result = check("Ma ostsin leib.", providers=[LLMGrammar("anthropic")])
    assert result.degraded and "Refused" in result.diagnostics
    assert not breaker.is_open("llm:anthropic")


def test_one_client_serves_every_call(monkeypatch):
    """A new client per call is a new TLS connection per learner request."""
    import anthropic

    made = []
    monkeypatch.setattr(claude, "_CLIENT", None)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: made.append(kw) or SimpleNamespace(
        with_options=lambda **opts: SimpleNamespace(timeout=opts["timeout"])))
    timeouts = [claude._client(t).timeout for t in (5.0, 10.0, 5.0)]
    assert len(made) == 1 and timeouts == [5.0, 10.0, 5.0]


def test_the_haiku_prompt_does_not_hold_the_eval_s_answers():
    """A prompt that lists an eval sentence as correct inflates that lane's clean
    pass rate, and the lane is promoted on a score it did not earn."""
    from eesti.evals.gec import CASES
    from eesti.providers.grammar import CLAUDE_PROMPT

    prompt = CLAUDE_PROMPT.casefold()
    leaked = [c.sentence for c in CASES if c.sentence.casefold().rstrip(".") in prompt]
    assert not leaked
