"""Speech recognition for the speaking exercises — as options, ranked honestly.

## What exists for Estonian, tested rather than assumed

| Option | State (probed, August 2026) |
|---|---|
| **TalTech `whisper-large-v3-turbo-et-verbatim-2604`** | MIT, ungated, **1 400 h** verbatim Estonian + 4 000 h broadcast news. **A GGML build was published 2026-06-17**, so it runs in whisper.cpp on a CPU. |
| The older `…-et-verbatim` | Superseded — its own model card points at the 2604 one. |
| **Hugging Face Inference Providers** | The TalTech models have `inferenceProviderMapping: {}` — **nobody hosts them**. Generic `openai/whisper-large-v3` has five providers and does support Estonian, less well. |
| TartuNLP speech-to-text | `api.tartunlp.ai/speech-to-text/*` still 404s. Dead since the repo was archived in 2024. |
| `tekstiks.ee` (TalTech) | The site is up and free for non-commercial use, but it is a SvelteKit app with no documented public API; its own page links to `est-asr-pipeline` for self-hosting. |
| Browser Web Speech API | Free and needs no infrastructure, but Estonian is not among the languages Safari or Chrome reliably support. Feature-detected in the UI, never assumed. |

## What that means, and why the chain is ordered this way

**The best Estonian model cannot be rented — but it can be run.** The GGML build
is the finding that changes things: whisper.cpp on Apple Silicon transcribes
faster than real time on CPU, so the most accurate option is also the free,
private one, on the machine the learner already owns. That also settles the
privacy question the research raised: text is disposable, a voice is biometric,
and this way the voice never leaves the laptop.

So: **local first, hosted second, and neither is required.** With no provider at
all the speaking tab still records and plays back, which is most of its value —
the B1 speaking exam is paired and dialogic, and no transcript scores that.

## What this deliberately does not do

**No pronunciation score.** Forced alignment yields timings, not correctness,
and turning that into feedback is a research project. EKI already publishes free
pronunciation exercises. A transcript is used for one honest thing: showing what
the recogniser *heard*, so the learner can compare it with what they meant.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

# Generous next to the text providers: a minute of audio takes real time to
# transcribe, and a learner who has just recorded is willing to wait for it.
TIMEOUT = 120.0

HF_MODEL = "openai/whisper-large-v3"
HF_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

# The Estonian model, for anyone self-hosting. Named here so the recommendation
# lives next to the code that would use it.
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
    return {
        "local": bool(binary and model),
        "hosted": bool(os.environ.get("HF_TOKEN")),
        "estonian_model": ESTONIAN_MODEL,
        "note": (
            "Local whisper.cpp with the TalTech Estonian model is the accurate "
            "and private option; the hosted fallback is generic Whisper, which "
            "knows Estonian less well."
        ),
    }


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


def transcribe(audio: bytes, mime: str = "audio/wav") -> Transcript:
    """Local first, hosted second, and an honest refusal third.

    The refusal matters: silence would look like a broken button, and the
    speaking tab is useful without a transcript — recording and playing back is
    most of what solo practice for a *paired* exam can offer.
    """
    suffix = ".wav" if "wav" in mime else ".webm" if "webm" in mime else ".ogg"
    for engine in (lambda: _local(audio, suffix), lambda: _hosted(audio, mime)):
        result = engine()
        if result is not None and result.text:
            return result
        if result is not None and result.degraded:
            return result
    return Transcript(
        "", "puudub", degraded=True,
        note=("Kõnetuvastust ei ole seadistatud. Salvestamine ja kuulamine "
              "töötavad; transkriptsiooniks vaata docs/speaking.md."),
    )
