"""Speech recognition for the speaking exercises — cloud-first, because the app is.

## The correction that shapes this file

An earlier version of this module recommended running whisper.cpp locally with
TalTech's Estonian GGML build. That is the most accurate and the most private
option, and it is **the wrong recommendation for this app**: this deploys to
Cloudflare, so "runs on your MacBook" is a thing that happens on a machine the
server is not. A learner on a phone gets nothing from it.

So the chain is ordered by *where the app actually runs*, and the local engine
stays only as a bonus for whoever runs `serve` on their own laptop.

## What was probed (August 2026), and what it costs

| Route | State | Estonian | Cost |
|---|---|---|---|
| **Cloudflare Workers AI `@cf/openai/whisper-large-v3-turbo`** | Live | Whisper's 99 languages; takes a `language` pin | **$0.00051/audio-minute**, plus the free daily neuron allowance |
| **OpenRouter, audio-input models** | 38 of them, one **free** (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`); Gemini Flash from ~$0.00000004/audio-token | Multilingual | free tier exists |
| Hugging Face `openai/whisper-large-v3` | Five providers | yes, generically | free tier |
| TalTech `…-et-verbatim-2604` | MIT, best Estonian, GGML build | best | **nobody hosts it** — `inferenceProviderMapping` is empty |
| `api.tartunlp.ai/speech-to-text` | 404 | — | dead since 2024 |

**Workers AI is the primary for three reasons that all point the same way:** it
is the platform the app already deploys to, its credentials
(`CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`) are already provisioned for
the LLM eval, and at half a thousandth of a dollar per audio minute a year of
daily practice costs less than a coffee. It also accepts `language="et"` — so
Estonian is pinned rather than guessed — and an `initial_prompt`, which is used
to feed it the question being answered so the vocabulary is biased correctly.

## Why not an Estonian LLM

Worth stating plainly, because it is the obvious question: **EstLLM cannot do
this.** `tartuNLP/Llama-3.1-EstLLM-8B-Instruct` is a text model — it has no
audio encoder, so it cannot turn a recording into words at any price. The
Estonian-specific speech models (TalTech's) are the ones that could, and nobody
rents them.

Where an Estonian-tuned model *does* belong is one step later: judging the
**transcript**. That runs through the existing LLM chain, on text, which is what
it is for.

## What this still refuses to do

**No pronunciation score.** Forced alignment yields timings, not correctness,
and EKI already publishes free pronunciation exercises. A transcript is used for
one honest thing: showing what the recogniser *heard*, so the learner can
compare it with what they meant.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

from . import breaker
from pathlib import Path

# Generous next to the text providers — a minute of audio takes real time to
# transcribe — but not four times generous. With four engines in series, 120 s
# each meant a full outage cost the learner eight minutes before telling them
# nothing was heard. 45 s is comfortably above what hosted Whisper needs for a
# short answer, and the circuit breaker below stops a dead engine being tried at
# all after two failures.
TIMEOUT = 45.0

CF_MODEL = "@cf/openai/whisper-large-v3-turbo"
CF_URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Free and audio-capable. Overridable, because a free model's availability is
# not a promise anyone made.
OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_ASR_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
)
TRANSCRIBE_PROMPT = (
    "Transcribe this Estonian speech verbatim. Output only the transcription, "
    "with no commentary, translation or explanation."
)

HF_MODEL = "openai/whisper-large-v3"
HF_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

# The best Estonian model, named here so the fact stays next to the code: it is
# MIT and it is better than any of the above at Estonian, and no one hosts it.
# Usable only by self-hosting — see docs/speaking.md.
ESTONIAN_MODEL = "TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604"
ESTONIAN_GGML = f"https://huggingface.co/{ESTONIAN_MODEL}/resolve/main/ggml/ggml-model.bin"


@dataclass(frozen=True)
class Transcript:
    text: str
    engine: str
    degraded: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _whisper_cpp_paths() -> tuple[str | None, str | None]:
    """The whisper.cpp binary and the Estonian model, if this machine has them."""
    binary = os.environ.get("WHISPER_CPP_BIN") or shutil.which("whisper-cli") \
        or shutil.which("whisper.cpp") or shutil.which("main")
    model = os.environ.get("WHISPER_CPP_MODEL")
    if model and not Path(model).exists():
        model = None
    return binary, model


def available() -> dict:
    """Which engines this deployment can actually use. Shown in the UI as-is."""
    binary, model = _whisper_cpp_paths()
    cloudflare = bool(
        os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    )
    engines = {
        "cloudflare": cloudflare,
        "openrouter": bool(os.environ.get("OPENROUTER_API_KEY")),
        "huggingface": bool(os.environ.get("HF_TOKEN")),
        "local": bool(binary and model),
    }
    return {
        **engines,
        # What is currently tripped, so a slow first recording after an outage
        # is explainable rather than mysterious.
        "breakers": breaker.state(),
        # Kept for the UI's single question: can this deployment transcribe?
        "ready": any(engines.values()),
        "hosted": engines["cloudflare"] or engines["openrouter"] or engines["huggingface"],
        "estonian_model": ESTONIAN_MODEL,
        "note": (
            "Cloudflare Workers AI runs on the platform this app deploys to and "
            "pins the language to Estonian. The best Estonian model is TalTech's, "
            "and nobody hosts it — see docs/speaking.md."
        ),
    }


def _cloudflare(audio: bytes, context: str = "") -> Transcript | None:
    """Whisper large-v3-turbo on the platform the app already runs on.

    `language="et"` matters: Whisper guesses otherwise, and a few seconds of
    accented Estonian is exactly the input it guesses wrong on. `initial_prompt`
    carries the question being answered, which biases the vocabulary towards the
    topic instead of leaving it to chance.
    """
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not (token and account):
        return None

    payload = {
        "audio": base64.b64encode(audio).decode("ascii"),
        "task": "transcribe",
        "language": "et",
        "vad_filter": True,
        # Whisper repeats itself on silence; these are its documented guards.
        "condition_on_previous_text": False,
    }
    if context:
        payload["initial_prompt"] = context[:220]

    req = urllib.request.Request(
        CF_URL.format(account=account, model=CF_MODEL),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return Transcript("", "workers-ai", degraded=True, note=str(exc)[:200])

    text = ((body.get("result") or {}).get("text") or "").strip()
    if not text:
        errors = body.get("errors") or body.get("messages") or body
        return Transcript("", "workers-ai", degraded=True, note=str(errors)[:200])
    return Transcript(text, f"Workers AI ({CF_MODEL})")


def _openrouter(audio: bytes, mime: str = "audio/wav", context: str = "") -> Transcript | None:
    """An audio-capable chat model, OpenAI-style. The free tier's fallback.

    Chat models transcribe by being asked to, which makes them chattier than a
    dedicated ASR: the prompt insists on the transcription alone, and anything
    that still arrives wrapped in commentary is the caller's to distrust.
    """
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None

    fmt = "wav" if "wav" in mime else "webm" if "webm" in mime else "mp3"
    prompt = TRANSCRIBE_PROMPT + (f" Context: {context[:150]}" if context else "")
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "input_audio",
                 "input_audio": {"data": base64.b64encode(audio).decode("ascii"),
                                 "format": fmt}},
            ],
        }],
        "temperature": 0,
    }
    req = urllib.request.Request(
        OPENROUTER_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError) as exc:
        return Transcript("", OPENROUTER_MODEL, degraded=True, note=str(exc)[:200])
    if not text:
        return Transcript("", OPENROUTER_MODEL, degraded=True, note="empty response")
    return Transcript(text, f"OpenRouter ({OPENROUTER_MODEL})")


def _local(audio: bytes, suffix: str = ".wav") -> Transcript | None:
    binary, model = _whisper_cpp_paths()
    if not (binary and model):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"clip{suffix}"
        path.write_bytes(audio)
        try:
            proc = subprocess.run(
                [binary, "-m", model, "-l", "et", "-nt", "-otxt", "-of",
                 str(path.with_suffix("")), str(path)],
                capture_output=True, timeout=TIMEOUT, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return Transcript("", "whisper.cpp", degraded=True, note=str(exc))
        out = path.with_suffix(".txt")
        if proc.returncode == 0 and out.exists():
            return Transcript(out.read_text(encoding="utf-8").strip(),
                              "whisper.cpp (TalTech et)")
        return Transcript("", "whisper.cpp", degraded=True,
                          note=proc.stderr.decode("utf-8", "replace")[-300:])


def _hosted(audio: bytes, mime: str = "audio/wav") -> Transcript | None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(
        HF_URL, data=audio,
        headers={"Authorization": f"Bearer {token}", "Content-Type": mime},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return Transcript("", HF_MODEL, degraded=True, note=str(exc))
    text = payload.get("text") if isinstance(payload, dict) else None
    if not text:
        return Transcript("", HF_MODEL, degraded=True, note=str(payload)[:200])
    return Transcript(text.strip(), f"{HF_MODEL} (üldmudel)")


def transcribe(audio: bytes, mime: str = "audio/wav", context: str = "") -> Transcript:
    """Cloudflare, then OpenRouter, then Hugging Face, then local — then a refusal.

    Ordered by where the app runs, not by which engine is best in the abstract.
    The local engine is last because a Cloudflare deployment has no laptop; it is
    still there so `serve` on a developer's machine gets the accurate Estonian
    model for free.

    Unlike the grammar chain, a *degraded* answer does not stop the walk: a
    Cloudflare hiccup should fall through to OpenRouter rather than end the
    attempt, because unlike a grammar check there is no offline engine behind it
    to degrade to.

    The final refusal matters: silence would look like a broken button, and the
    speaking tab is useful without a transcript — recording and playing back is
    most of what solo practice for a *paired* exam can offer.
    """
    suffix = ".wav" if "wav" in mime else ".webm" if "webm" in mime else ".ogg"
    attempts = (
        ("workers-ai", lambda: _cloudflare(audio, context)),
        ("openrouter-audio", lambda: _openrouter(audio, mime, context)),
        ("hf-whisper", lambda: _hosted(audio, mime)),
        ("whisper.cpp", lambda: _local(audio, suffix)),
    )
    first_failure: Transcript | None = None
    for name, engine in attempts:
        if breaker.is_open(name):
            continue                      # tripped; do not pay its timeout again
        result = engine()
        if result is None:
            continue                      # not configured; not a failure
        if result.text:
            breaker.record_success(name)
            return result
        breaker.record_failure(name)
        first_failure = first_failure or result

    if first_failure is not None:
        return first_failure
    return Transcript(
        "", "puudub", degraded=True,
        note=("Kõnetuvastust ei ole seadistatud. Salvestamine ja kuulamine "
              "töötavad; transkriptsiooniks vaata docs/speaking.md."),
    )
