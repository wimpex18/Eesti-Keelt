"""What a 429 costs, and why retrying one is usually wrong here.

The deployment reported `llm:openrouter: HTTPError 429` on three consecutive
days. The free tier allows **20 requests a minute and 50 a day**, and — the
part that decides this design — **a failed attempt still counts against the
daily quota**.

So when the daily cap is what was hit, every retry spends another of the fifty
to be told the same thing. At `RETRIES = 3` a single grammar check cost three
requests and made the learner wait 5 s then 10 s to reach the answer the first
call already had. Ten checks a day would have spent 30 of the 50 on failures
alone.

Two different limits wear one status code, and only one of them is worth
sleeping through. The provider is the only thing that knows which, and it says
so in `Retry-After`.
"""

from __future__ import annotations

import io
import urllib.error

import pytest

from eesti.providers import llm


def http_error(code=429, headers=None):
    return urllib.error.HTTPError(
        "https://openrouter.ai/api/v1/chat/completions", code, "boom",
        headers or {}, io.BytesIO(b""))


@pytest.fixture(autouse=True)
def no_sleeping(monkeypatch):
    """Neither the throttle nor the backoff should make the suite slow, and a
    key must be present or `complete` refuses before it ever reaches the
    request this file is about."""
    monkeypatch.setattr(llm.time, "sleep", lambda *_: None)
    monkeypatch.setattr(llm, "_throttle", lambda: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def _count_calls(monkeypatch, error):
    calls = []

    def urlopen(*a, **k):
        calls.append(1)
        raise error

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    return calls


class TestWhatARateLimitCosts:
    def test_a_daily_cap_is_not_retried(self, monkeypatch):
        """The expensive case. A long `Retry-After` means the quota is spent,
        and three attempts spend three of it confirming that."""
        calls = _count_calls(monkeypatch, http_error(
            headers={"Retry-After": "3600"}))
        with pytest.raises(urllib.error.HTTPError):
            llm.complete("openrouter", "sa oled abiline", "hei")
        assert len(calls) == 1, f"spent {len(calls)} requests on a spent quota"

    def test_an_unexplained_429_is_not_retried_either(self, monkeypatch):
        """With no header there is no way to tell which cap it was, and
        guessing costs quota. Falling through the chain is cheap; that is what
        the chain is for."""
        calls = _count_calls(monkeypatch, http_error())
        with pytest.raises(urllib.error.HTTPError):
            llm.complete("openrouter", "sa oled abiline", "hei")
        assert len(calls) == 1

    def test_a_short_wait_is_retried(self, monkeypatch):
        """The per-minute cap clears on its own and is worth sleeping through
        — this is the 429 that retrying was written for."""
        calls = _count_calls(monkeypatch, http_error(
            headers={"Retry-After": "2"}))
        with pytest.raises(urllib.error.HTTPError):
            llm.complete("openrouter", "sa oled abiline", "hei")
        assert len(calls) == llm.RETRIES

    def test_the_reset_header_is_read_too(self, monkeypatch):
        """OpenRouter sends `X-RateLimit-Reset` as Unix milliseconds. Reading
        only `Retry-After` would treat a stated short wait as unknown."""
        import time

        soon = str(int((time.time() + 5) * 1000))
        calls = _count_calls(monkeypatch, http_error(
            headers={"X-RateLimit-Reset": soon}))
        with pytest.raises(urllib.error.HTTPError):
            llm.complete("openrouter", "sa oled abiline", "hei")
        assert len(calls) == llm.RETRIES

    def test_a_server_error_is_still_retried(self, monkeypatch):
        """5xx is the provider having a moment and costs no quota."""
        calls = _count_calls(monkeypatch, http_error(code=503))
        with pytest.raises(urllib.error.HTTPError):
            llm.complete("openrouter", "sa oled abiline", "hei")
        assert len(calls) == llm.RETRIES

    def test_a_bad_request_is_never_retried(self, monkeypatch):
        """4xx that is not 429 is us, and asking again changes nothing."""
        calls = _count_calls(monkeypatch, http_error(code=400))
        with pytest.raises(urllib.error.HTTPError):
            llm.complete("openrouter", "sa oled abiline", "hei")
        assert len(calls) == 1

    def test_a_dead_key_is_never_retried(self, monkeypatch):
        calls = _count_calls(monkeypatch, http_error(code=401))
        with pytest.raises(urllib.error.HTTPError):
            llm.complete("openrouter", "sa oled abiline", "hei")
        assert len(calls) == 1


class TestTheChainStillFallsThrough:
    def test_a_rate_limited_provider_does_not_stop_the_chain(self, monkeypatch):
        """The learner gets offline evidence rather than an error page, and the
        note names the status so the operator can tell 429 from 401."""
        from eesti.providers import breaker, grammar

        breaker.reset()
        monkeypatch.setattr(llm.urllib.request, "urlopen",
                            lambda *a, **k: (_ for _ in ()).throw(http_error()))
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        result = grammar.check("Ma lugesin raamatut läbi")
        assert result.engine
        assert "429" in result.note
