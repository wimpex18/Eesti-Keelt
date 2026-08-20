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
        return os.environ.get(self.key_env) if self.key_env else None

    @property
    def available(self) -> bool:
        """A provider is available when it has what it needs to be called.

        For a hosted provider that is a key. For a self-hosted one there is no
        key to have, so availability is a deliberate opt-in: set `LOCAL_LLM_URL`
        and the lane turns on. Treating "no key" as "unavailable" would have
        made a keyless provider permanently invisible.
        """
        if not self.key_env:
            return bool(os.environ.get("LOCAL_LLM_URL"))
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
        # Was `nvidia/nemotron-3-super-120b-a12b:free`, which this project's own
        # eval scored 0.50 recall / 0.50 precision -- and failed in the harmful
        # direction, flagging `Ma ostsin uue auto` and `Ma sõin suppi`, both
        # correct, while missing both irregular-verb errors. A learner following
        # it would be taught that correct Estonian is wrong.
        #
        # Gemma is what the research picked as the replacement and what
        # `.github/workflows/eval.yml` has defaulted to since: the OmniGEC study
        # (arXiv 2509.14504) found Gemma's largest multilingual GEC gain was on
        # Estonian, +8.25 GLEU. Unmeasured here until the eval is re-run against
        # it -- the point of switching is to be able to measure it.
        "google/gemma-4-26b-a4b-it:free",
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
    # EstLLM, run by you rather than by anyone else.
    #
    # This lane used to point at `router.huggingface.co` on the theory that it
    # was "the only hosted way to reach EstLLM". Probed on 2026-08-20: the
    # router serves 132 models and **not one Estonian one**, and every Estonian
    # model -- EstLLM, gec-llm, Llammas, TalTech's verbatim Whisper -- has an
    # empty `inferenceProviderMapping`. Nobody hosts any of them. The lane could
    # never have answered, and it was not in `LLM_PREFERENCE` either, so nothing
    # ever tried it and nothing ever noticed.
    #
    # The model is still the right idea: a general model failing Estonian object
    # case is exactly what an Estonian-adapted one should fix. It just needs a
    # machine instead of a key. GGUF builds exist (`mradermacher/
    # Llama-3.1-EstLLM-8B-Instruct-1125-GGUF`, Q4_K_M ~4.9 GB), and Ollama,
    # LM Studio and llama.cpp all expose an OpenAI-compatible `/v1`. So the lane
    # points at whatever is serving on `LOCAL_LLM_URL`.
    #
    # Keyless on purpose: a local server has nothing to authenticate. See
    # docs/local-llm.md for the Mac mini setup and the tunnel, if the deployment
    # is to reach it rather than just `cli serve`.
    "local": Provider(
        "local",
        os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1"),
        "",  # no key: the server is yours
        os.environ.get("LOCAL_LLM_MODEL", "hf.co/mradermacher/"
                       "Llama-3.1-EstLLM-8B-Instruct-1125-GGUF:Q4_K_M"),
        "Free and private. Only reachable where the server is: localhost for "
        "`cli serve`, or a tunnel for the deployment.",
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
    # Resolved at call time so a URL set after import still takes effect --
    # the same rule the rest of this project follows for paths.
    if provider.name == "local":
        return os.environ.get("LOCAL_LLM_URL", provider.base_url).rstrip("/")
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
