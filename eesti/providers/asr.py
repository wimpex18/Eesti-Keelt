"""Speech recognition for the speaking exercises.

Ordered by where the app runs (Cloud Run, behind the Worker):

| Route | Notes |
|---|---|
| Cloudflare Workers AI `@cf/openai/whisper-large-v3-turbo` | primary; `language="et"`, `initial_prompt` carries the question |
| OpenRouter audio-input models | fallback |
| Hugging Face `openai/whisper-large-v3` (`HF_TOKEN`) | fallback |
| TalTech Whisper `…-et-verbatim-2604` via whisper.cpp | best Estonian; local only |
| TalTech Voxtral via llama.cpp | local only |

In production the Worker answers `/api/transcribe` through its `AI` binding;
this chain serves `cli serve`. EstLLM is a text model and cannot transcribe.
No pronunciation score: a transcript shows what the recogniser heard.
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

# Longer than text providers (audio takes time), bounded so several engines in
# series cannot keep the learner waiting minutes; the breaker skips dead engines.
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

# TalTech's Estonian verbatim Whisper (MIT); self-hosted only, via whisper.cpp.
ESTONIAN_MODEL = "TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604"

# TalTech's Estonian Voxtral (`TalTechNLP/Voxtral-Mini-3B-2507-estonian`; GGUF
# builds by the third-party requantiser `mradermacher`) needs an instruction and
# the `mmproj` audio encoder, via llama.cpp's multimodal CLI. It is behind
# whisper.cpp because its reported WER rests on ten recordings. The prompt asks
# for a verbatim transcription; unprompted it may summarise instead.
VOXTRAL_PROMPT = TRANSCRIBE_PROMPT


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


def _voxtral_paths() -> tuple[str | None, str | None, str | None]:
    """The llama.cpp multimodal binary, the Voxtral weights and its audio encoder —
    all three or nothing: without `mmproj` the model answers about audio it never
    received.
    """
    binary = os.environ.get("VOXTRAL_BIN") or shutil.which("llama-mtmd-cli")
    model = os.environ.get("VOXTRAL_MODEL_PATH")
    mmproj = os.environ.get("VOXTRAL_MMPROJ")
    if model and not Path(model).exists():
        model = None
    if mmproj and not Path(mmproj).exists():
        mmproj = None
    if not (binary and model and mmproj):
        return None, None, None
    return binary, model, mmproj


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
        "voxtral": all(_voxtral_paths()),
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
    """Whisper large-v3-turbo on Workers AI, with `language="et"` pinned and the
    question as `initial_prompt` to bias vocabulary.
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
    """An audio-capable chat model, OpenAI-style: asked for the transcription alone."""
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


def _voxtral(audio: bytes, suffix: str = ".wav") -> Transcript | None:
    """TalTech's Estonian Voxtral through llama.cpp's multimodal CLI: the answer is
    stdout (logs go to stderr), trimmed.
    """
    binary, model, mmproj = _voxtral_paths()
    if not (binary and model and mmproj):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"clip{suffix}"
        path.write_bytes(audio)
        try:
            proc = subprocess.run(
                [binary, "-m", model, "--mmproj", mmproj,
                 "--audio", str(path), "-p", VOXTRAL_PROMPT],
                capture_output=True, timeout=TIMEOUT, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return Transcript("", "voxtral", degraded=True, note=str(exc))
        text = proc.stdout.decode("utf-8", "replace").strip()
        if proc.returncode == 0 and text:
            return Transcript(text, "voxtral (TalTech et)")
        return Transcript("", "voxtral", degraded=True,
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
    """Workers AI, OpenRouter, Hugging Face, then the two local engines.

    whisper.cpp precedes Voxtral: its Estonian record is published, Voxtral's is
    not established. A degraded answer does not stop the walk — there is no offline
    engine to fall back to. With nothing configured, the refusal says recording and
    playback still work.
    """
    suffix = ".wav" if "wav" in mime else ".webm" if "webm" in mime else ".ogg"
    attempts = (
        ("workers-ai", lambda: _cloudflare(audio, context)),
        ("openrouter-audio", lambda: _openrouter(audio, mime, context)),
        ("hf-whisper", lambda: _hosted(audio, mime)),
        ("whisper.cpp", lambda: _local(audio, suffix)),
        ("voxtral", lambda: _voxtral(audio, suffix)),
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
