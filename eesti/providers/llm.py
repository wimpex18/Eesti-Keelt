"""Unified LLM client for the OpenAI-compatible providers.

OpenRouter, Groq and Cloudflare Workers AI all speak the OpenAI chat-completions
shape, so one client covers them and switching provider is a base-URL change.

Two rules encoded here, both learned the hard way (see docs/ai-strategy.md):

1. **Never pin a model id without probing it.** Ids are withdrawn silently, and a
   withdrawn `:free` id is especially treacherous because the paid one with the
   same name keeps existing — the name still looks right while every call 404s.
   `list_models()` and `probe()` exist so a pin can be checked, not trusted.
2. **The model never generates linguistic facts.** It adjudicates free text and
   explains. Forms come from Vabamorf via the exported dataset.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_TIMEOUT = 60.0

# OpenRouter's free tier caps at 20 requests/minute, and the eval fires 18 in a
# row — a real run lost two cases to HTTP 429. Pace requests and retry the
# transient failures, or the score measures our impatience rather than the model.
MIN_INTERVAL = 3.5
RETRIES = 3
_last_call = 0.0


def _throttle() -> None:
    global _last_call
    wait = MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    key_env: str
    default_model: str
    # Free-tier shape, for choosing at runtime. None = paid/unmetered.
    free_note: str = ""

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.key_env)

    @property
    def available(self) -> bool:
        return bool(self.api_key)


# Probed against the live catalogues in August 2026. Re-probe before trusting:
#   python -m eesti.cli models --provider openrouter
PROVIDERS: dict[str, Provider] = {
    # 15 of 412 OpenRouter models were :free at time of probing. This id was
    # present and advertises structured_outputs, which the JSON contract needs.
    "openrouter": Provider(
        "openrouter",
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "50 req/day free; 1000/day after a one-time $10 credit purchase "
        "(an account threshold, not consumption). 20 req/min either way.",
    ),
    "groq": Provider(
        "groq",
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        "llama-3.3-70b-versatile",
        "Generous free tier, fastest inference. Rate-limited per model.",
    ),
    # Runs inside Cloudflare, so an edge deployment pays no egress and needs no
    # third-party key. Requires CF_ACCOUNT_ID as well as the token.
    "workers-ai": Provider(
        "workers-ai",
        "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        "CLOUDFLARE_API_TOKEN",
        "@cf/openai/gpt-oss-120b",
        "10,000 neurons/day free, shared across all models.",
    ),
    "anthropic": Provider(
        "anthropic",
        "https://api.anthropic.com/v1",
        "ANTHROPIC_API_KEY",
        "claude-sonnet-5",
        "Paid. Cents/month at a few checks a day.",
    ),
}


def _base_url(provider: Provider) -> str:
    if "{account_id}" in provider.base_url:
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        if not account:
            raise RuntimeError("CLOUDFLARE_ACCOUNT_ID is required for workers-ai")
        return provider.base_url.format(account_id=account)
    return provider.base_url


def list_models(provider_name: str, timeout: float = 30.0) -> list[dict]:
    """Fetch the provider's live catalogue.

    OpenRouter serves this without a key, which makes it the cheapest way to
    check whether a pinned id still exists.
    """
    provider = PROVIDERS[provider_name]
    req = urllib.request.Request(f"{_base_url(provider)}/models")
    if provider.api_key:
        req.add_header("Authorization", f"Bearer {provider.api_key}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read()).get("data", [])


def probe(provider_name: str, model: str) -> bool:
    """True if `model` is present in the provider's catalogue right now."""
    try:
        return any(m.get("id") == model for m in list_models(provider_name))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, KeyError):
        return False


def complete(
    provider_name: str,
    system: str,
    user: str,
    model: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_tokens: int = 2000,
    json_mode: bool = True,
) -> str:
    """One chat completion. Returns the assistant's text."""
    provider = PROVIDERS[provider_name]
    if not provider.available:
        raise RuntimeError(f"{provider.key_env} is not set")

    payload: dict = {
        "model": model or provider.default_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{_base_url(provider)}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider.api_key}",
        },
    )

    for attempt in range(RETRIES):
        _throttle()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read())
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            # 429 and 5xx are the provider having a moment; 4xx otherwise is us.
            retryable = exc.code == 429 or exc.code >= 500
            if not retryable or attempt == RETRIES - 1:
                raise
            # Honour Retry-After when the provider sends one.
            delay = exc.headers.get("Retry-After")
            time.sleep(float(delay) if delay and delay.isdigit() else 5 * (attempt + 1))
        except (TimeoutError, OSError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt)

    raise RuntimeError("unreachable")


def parse_json(raw: str) -> dict:
    """Parse a model's JSON reply, tolerating a fenced code block around it."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)
