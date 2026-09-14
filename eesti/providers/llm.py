"""One client for every OpenAI-compatible LLM lane.

Rules:

1. **Never pin a model id without probing it** — ids are withdrawn silently.
   `list_models()` checks a pin against the live catalogue.
2. **The model never generates linguistic facts.** It explains; forms come
   from Vabamorf. See `docs/ai-boundaries.md` and `docs/ai-providers.md`.
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
    #: Whether the lane accepts `response_format: {"type": "json_object"}`.
    #: Where unsupported, the prompt still demands JSON and `parse_json`
    #: tolerates a fenced block.
    json_mode: bool = True

    @property
    def model(self) -> str:
        """The model to call: `<LANE>_MODEL` (or `LOCAL_LLM_MODEL`) overrides the pin."""
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
        """Available when it has what it needs: a key for hosted lanes, `LOCAL_LLM_URL`
        for the keyless local lane.
        """
        if not self.key_env:
            return bool(os.environ.get("LOCAL_LLM_URL"))
        return bool(self.api_key)


# Order of use is `grammar.LLM_PREFERENCE`; measurements are in docs/ai-providers.md.
# Re-check a pin with `python -m eesti.cli models --provider <name>`.
PROVIDERS: dict[str, Provider] = {
    # Cloudflare Workers AI over REST. Token needs Account → Workers AI → Read.
    "workers-ai": Provider(
        "workers-ai",
        "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        "CLOUDFLARE_API_TOKEN",
        "@cf/openai/gpt-oss-120b",
        "10,000 neurons/day free, shared across all models.",
    ),
    # NVIDIA Build. JSON mode is not documented per model, so it is not sent.
    "nvidia": Provider(
        "nvidia",
        "https://integrate.api.nvidia.com/v1",
        "NVIDIA_API_KEY",
        "deepseek-ai/deepseek-v4-flash-0731",
        "Free NVIDIA Developer Program key, 40 req/min; 100+ hosted models.",
        json_mode=False,
    ),
    # Mistral Experiment plan. `-latest` is Mistral's stable alias.
    "mistral": Provider(
        "mistral",
        "https://api.mistral.ai/v1",
        "MISTRAL_API_KEY",
        "mistral-large-latest",
        "Free Experiment plan, ~1B tokens/month, rate-limited.",
    ),
    # Free models rotate; a `:free` id can vanish while the paid id remains.
    "openrouter": Provider(
        "openrouter",
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        "dots-studio/dots-3-note-preview:free",
        "50 req/day free; 1000/day after a one-time $10 credit purchase "
        "(an account threshold, not consumption). 20 req/min either way.",
    ),
    # EstLLM (Estonian-adapted Llama 3.1 8B) on your own OpenAI-compatible
    # server (Ollama, LM Studio, llama.cpp). Keyless; on when LOCAL_LLM_URL is set.
    "local": Provider(
        "local",
        os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1"),
        "",  # no key: the server is yours
        "hf.co/mradermacher/Llama-3.1-EstLLM-8B-Instruct-1125-GGUF:Q4_K_M",
        "Free and private. Only reachable where the server is: localhost for "
        "`cli serve`, or a tunnel for the deployment.",
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


class EmptyReply(RuntimeError):
    """The provider answered, with no text in it."""

    def __init__(self, finish_reason: str):
        super().__init__(f"empty reply (finish_reason={finish_reason})")
        self.finish_reason = finish_reason


def _user_agent() -> str:
    """This app's User-Agent (`net.UA`); some provider firewalls refuse urllib's default."""
    from ..net import UA

    return UA


def list_models(provider_name: str, timeout: float = 30.0) -> list[dict]:
    """Fetch the provider's live catalogue."""
    provider = PROVIDERS[provider_name]
    url = f"{_base_url(provider)}/models"
    if provider.name == "workers-ai":
        # The OpenAI-compatible base has no catalogue; use `/ai/models/search`.
        url = _base_url(provider).removesuffix("/v1") + "/models/search"
    req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    if provider.api_key:
        req.add_header("Authorization", f"Bearer {provider.api_key}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read())
    if provider.name == "workers-ai":
        return [{**m, "id": m.get("name") or m.get("id", "")} for m in body.get("result") or []]
    return body.get("data", [])


def probe(provider_name: str, model: str) -> bool:
    """True if `model` is present in the provider's catalogue right now."""
    try:
        return any(m.get("id") == model for m in list_models(provider_name))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, KeyError):
        return False


#: The longest `Retry-After` worth sleeping through mid-request. Above this the
#: 429 is a daily cap rather than a per-minute one, and the right move is to
#: fall through the chain rather than to spend more quota confirming it.
RETRY_CEILING = 60.0


def _retry_after(exc) -> float | None:
    """Seconds the provider asks us to wait, or None: `Retry-After` (seconds or an
    HTTP date) or OpenRouter's `X-RateLimit-Reset` (Unix ms).
    """
    import email.utils

    raw = exc.headers.get("Retry-After") if exc.headers else None
    if raw:
        raw = raw.strip()
        if raw.replace(".", "", 1).isdigit():
            return float(raw)
        stamp = email.utils.parsedate_to_datetime(raw)
        if stamp is not None:
            import datetime as _dt

            now = _dt.datetime.now(stamp.tzinfo or _dt.timezone.utc)
            return max(0.0, (stamp - now).total_seconds())
    reset = exc.headers.get("X-RateLimit-Reset") if exc.headers else None
    if reset and reset.strip().isdigit():
        return max(0.0, int(reset) / 1000.0 - time.time())
    return None


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
        # Temperature 0 on every lane (all are OpenAI-compatible and accept it).
        "temperature": 0,
    }
    # Both must agree: the caller wants JSON, and the lane can ask for it. A
    # provider that cannot is not asked, and is told in the prompt instead.
    if json_mode and provider.json_mode:
        payload["response_format"] = {"type": "json_object"}

    # A keyless lane -- a local server -- has nothing to authenticate, and
    # `Bearer None` is a header that happens to work only because Ollama
    # ignores it. Send it when there is a key and not when there is not.
    headers = {"Content-Type": "application/json", "User-Agent": _user_agent()}
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
            choice = body["choices"][0]
            content = choice["message"].get("content")
            if not content:
                # A reasoning model that spends its budget thinking returns no content.
                raise EmptyReply(choice.get("finish_reason") or "unknown")
            return content
        except urllib.error.HTTPError as exc:
            if attempt == RETRIES - 1:
                raise
            if exc.code == 429:
                # Two 429s share one status code. A per-minute limit is worth a short wait; a
                # daily cap is not, and on OpenRouter a failed attempt still counts against the
                # daily quota. Retry only when `Retry-After` asks for a short wait; otherwise fall
                # through to the next lane.
                wait = _retry_after(exc)
                if wait is None or wait > RETRY_CEILING:
                    raise
                time.sleep(wait)
                continue
            if exc.code < 500:
                raise          # 4xx that is not 429 is us, not them
            time.sleep(5 * (attempt + 1))
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
