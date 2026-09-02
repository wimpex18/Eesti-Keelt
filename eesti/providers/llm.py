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
    #: Does this lane accept `response_format: {"type": "json_object"}`?
    #:
    #: False for the HF router, and the distinction is not cosmetic: the router
    #: picks a provider by the capabilities the *request* asks for, so asking
    #: for JSON mode on a model whose only provider cannot do it is not a
    #: degraded answer, it is **no route at all** — answered `400
    #: model_not_supported`, which reads as "wrong model id" and is not.
    #:
    #: Measured 2026-09-02. The same model, same account, same token, answered
    #: from the model page's own widget seconds later — because that widget
    #: does not ask for JSON mode. Every one of the eval's 18 cases failed;
    #: nothing about the model was learned.
    #:
    #: Dropping the flag costs nothing here. `SYSTEM` already says "Return ONLY
    #: valid JSON" and `parse_json` already tolerates a fenced block, because
    #: providers were returning prose-wrapped JSON long before this.
    json_mode: bool = True

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
    # This entry is rule 1 above, demonstrated on itself. It was pinned to
    # `llama-3.3-70b-versatile` and probed against the live catalogue in August
    # 2026; Groq announced that id's deprecation for the free and developer
    # tiers on **2026-08-16**, and the pin was stale six days later, on the
    # first day a key was ever put behind it. A withdrawn id that enterprise
    # accounts keep does not 404 -- the resource exists and this account may not
    # have it -- so it answers **403**, which reads as a permissions problem and
    # sent the first diagnosis at the key rather than at the model.
    #
    # `openai/gpt-oss-120b` rather than `qwen/qwen3.6-27b`, and the reason is
    # not capability. Qwen is the better fit on the axis the OpenRouter comment
    # above spends four paragraphs on -- 27B dense against roughly 5B active --
    # and Groq lists it as **preview**, "for evaluation purposes only", which is
    # a documented promise to withdraw it. This lane exists to answer on the
    # days the primary cannot; pinning it to something that announces its own
    # impermanence rebuilds the failure being fixed here. Production tier wins
    # for a backstop, and it is the model the `workers-ai` lane already runs, so
    # falling through does not also change models.
    #
    # The active-parameter objection stands and is not settled by this choice.
    # `GROQ_MODEL` is why it does not have to be: trying qwen against the eval
    # is an environment variable, not a redeploy.
    "groq": Provider(
        "groq",
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        "openai/gpt-oss-120b",
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
    # EstLLM on somebody else's machine.
    #
    # This lane existed once, pointing at `router.huggingface.co` on the theory
    # that it was "the only hosted way to reach EstLLM", and it was deleted
    # after the 2026-08-20 probe: the router served 132 models and **not one
    # Estonian one**, every Estonian model had an empty
    # `inferenceProviderMapping`, and the lane was not in `LLM_PREFERENCE`
    # either. Defined, unreachable, unnoticed.
    #
    # It is back because the measurement changed, not because the idea did.
    # Re-probed 2026-09-01: `tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125` -- the
    # exact id this project pins -- reports `featherless-ai`, status `live`,
    # task `conversational`. A claim about somebody else's infrastructure is a
    # measurement, and this one went stale in three weeks in the direction that
    # kept the project from noticing an option it had been waiting for.
    #
    # **Two things are asserted here and one is not.** The mapping is read from
    # the model's own metadata, and the router speaks the OpenAI shape this
    # client already sends. What is *not* verified from this repository is that
    # a request actually completes: the router answers 401 before it routes, so
    # an unauthenticated probe returns 401 for a real id and for a made-up one
    # alike and proves nothing. Only a call with a token settles it, and this
    # repository must never hold one. So this lane is offered, not promised --
    # `cli eval --provider huggingface` is how it gets a number.
    #
    # Placed directly after `local` in `LLM_PREFERENCE` for one reason: it runs
    # **the same Estonian-adapted model**, on hardware somebody else owns. The
    # argument that puts `local` in front of the general models is an argument
    # about the model, and it applies here unchanged; the only thing that
    # separates the two lanes is who pays and who can read the request.
    #
    # `HF_TOKEN` is already this deployment's vocabulary -- `providers/asr.py`
    # reads it for hosted Whisper -- so turning this on adds a lane, not a
    # secret.
    "huggingface": Provider(
        "huggingface",
        "https://router.huggingface.co/v1",
        "HF_TOKEN",
        "tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125",
        "Routed to featherless-ai; that provider's own free/paid tiers apply. "
        "Estonian-adapted weights without owning a machine.",
        json_mode=False,
    ),
    # The same model, run by you rather than by anyone else.
    #
    # A general model failing Estonian object case is exactly what an
    # Estonian-adapted one should fix, and this is the lane where that costs
    # nothing and tells nobody. GGUF builds exist (`mradermacher/
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


#: The longest `Retry-After` worth sleeping through mid-request. Above this the
#: 429 is a daily cap rather than a per-minute one, and the right move is to
#: fall through the chain rather than to spend more quota confirming it.
RETRY_CEILING = 60.0


def _retry_after(exc) -> float | None:
    """Seconds the provider asks us to wait, or None if it did not say.

    `Retry-After` is either a count of seconds or an HTTP date; OpenRouter also
    sends `X-RateLimit-Reset` as a Unix timestamp in milliseconds. Read all
    three rather than only the easy one -- guessing here is what costs quota.
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
        # Grading here is deterministic and that is the one property that must
        # not break. Every remaining lane is OpenAI-compatible and accepts it;
        # the one that did not -- `anthropic`, where sampling parameters are
        # removed on `claude-sonnet-5` -- was deleted rather than special-cased,
        # so the per-provider flag that briefly guarded it went with it.
        "temperature": 0,
    }
    # Both must agree: the caller wants JSON, and the lane can ask for it. A
    # provider that cannot is not asked, and is told in the prompt instead.
    if json_mode and provider.json_mode:
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
            if attempt == RETRIES - 1:
                raise
            if exc.code == 429:
                # Two different 429s wear one status code, and retrying is
                # right for exactly one of them.
                #
                # OpenRouter's free tier allows 20 requests a minute and 50 a
                # day, and **a failed attempt still counts against the daily
                # quota**. So when the daily cap is what was hit, every retry
                # spends another of the 50 to be told the same thing, and the
                # learner waits 5s then 10s to arrive at the answer the first
                # call already gave. Three requests and fifteen seconds for one
                # guaranteed failure -- and the whole point of a provider chain
                # is that falling through to the next one is cheap.
                #
                # The provider is the only thing that knows which cap it was,
                # and it says so in `Retry-After`. A short wait is the
                # per-minute cap and worth sleeping through; a long one, or none
                # at all, is not something to spend quota guessing about.
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
