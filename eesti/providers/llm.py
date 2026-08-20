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
    def model(self) -> str:
        """The model to call, overridable per provider from the environment.

        `OPENROUTER_MODEL`, `GROQ_MODEL`, `LOCAL_LLM_MODEL` and so on. Trying a
        different model was a code change and a redeploy until now, which is a
        high price for an experiment whose whole point is that the answer is
        unknown — and this project has already run the wrong model in production
        for weeks because switching it meant editing a constant.
        """
        # `local` reads LOCAL_LLM_MODEL, to pair with LOCAL_LLM_URL rather than
        # inventing a second naming convention next to it. Everything else is
        # NAME_MODEL, with dashes normalised: WORKERS_AI_MODEL.
        names = ["LOCAL_LLM_MODEL"] if self.name == "local" else []
        names.append(f"{self.name.upper().replace('-', '_')}_MODEL")
        for name in names:
            value = os.environ.get(name)
            if value:
                return value
        return self.default_model

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
        # Chosen on evidence rather than on an eval, because the eval needs a
        # key this repository must never hold. Three things decided it.
        #
        # 1. **Active parameters, not total.** The Estonian benchmark work
        #    (Lillepalu & Alumäe, LREC 2026) frames weak Estonian as either
        #    less training data *or* "less model capacity dedicated to that
        #    language". Of the eight free models that accept the
        #    `response_format` this client sends, active capacity runs:
        #    gemma-4-31b **30.7B dense**, dots-3-note 16B, nemotron-3-super
        #    12B, gemma-4-26b-a4b **3.8B**, gpt-oss-20b 3.6B.
        #
        #    `nvidia/nemotron-3-super-120b-a12b:free` -- 12B active -- is the
        #    one this project measured at 0.50 recall / 0.50 precision, failing
        #    in the harmful direction: it flagged `Ma ostsin uue auto` and
        #    `Ma sõin suppi`, both correct. `gemma-4-26b-a4b:free` was picked as
        #    its replacement and is a **downgrade** on this axis at 3.8B active,
        #    which is the opposite of what a low-resource language needs.
        #
        # 2. **Gemma lineage.** The OmniGEC study (arXiv 2509.14504) found
        #    Gemma's largest multilingual GEC gain was on Estonian, +8.25 GLEU.
        #
        # 3. **It takes the parameter we send.** `structured_outputs` and
        #    `response_format` are different capabilities; this client sends
        #    the latter, and gemma-4-31b accepts it.
        #
        # Still unmeasured on this project's own eval, and said plainly rather
        # than implied: this is the best-evidenced choice available without a
        # key, not a result. `docs/ai-strategy.md` has the paid upgrade, which
        # costs about $0.20 a month and is what the evidence actually favours.
        "google/gemma-4-31b-it:free",
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
        "hf.co/mradermacher/Llama-3.1-EstLLM-8B-Instruct-1125-GGUF:Q4_K_M",
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
        raise RuntimeError(
            f"{provider.key_env} is not set" if provider.key_env
            else f"{provider.name}: LOCAL_LLM_URL is not set"
        )

    payload: dict = {
        "model": model or provider.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    # A keyless lane -- a local server -- has nothing to authenticate, and
    # `Bearer None` is a header that happens to work only because Ollama
    # ignores it. Send it when there is a key and not when there is not.
    headers = {"Content-Type": "application/json"}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"

    req = urllib.request.Request(
        f"{_base_url(provider)}/chat/completions",
        data=json.dumps(payload).encode(),
        headers=headers,
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
