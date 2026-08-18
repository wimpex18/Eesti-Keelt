"""Estonian speech synthesis via TartuNLP's public TTS API.

Unlike the grammar service this one is genuinely reliable — during research it
returned a 310 KB WAV in 2.0s with no auth. It is what makes listening practice
possible from *any* text: a textbook passage, a harvested ERR transcript, or a
generated drill sentence.

Output is cached on disk by content hash, so repeated listening costs nothing and
works offline once fetched.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

from ..config import CACHE, PROVIDER_TIMEOUT, TARTUNLP_TTS

# Verified available voices (12 Estonian + 2 Voro). "mari" is a clear default.
VOICES = (
    "mari", "tambet", "liivika", "kalev", "kylli", "meelis",
    "albert", "indrek", "vesta", "peeter", "luukas", "lee",
)
DEFAULT_VOICE = "mari"

# Slower than natural speech: at A1-A2 the bottleneck is parsing speed, not
# vocabulary, and 0.7 keeps prosody natural while staying followable.
LEARNER_SPEED = 0.7


def cache_path(text: str, speaker: str, speed: float, cache_dir: Path | None = None) -> Path:
    digest = hashlib.sha256(
        f"{speaker}|{speed}|{text}".encode("utf-8")
    ).hexdigest()[:20]
    return Path(cache_dir or CACHE) / "audio" / f"{digest}.wav"


def synthesize(
    text: str,
    speaker: str = DEFAULT_VOICE,
    speed: float = LEARNER_SPEED,
    cache_dir: Path | None = None,
    timeout: float = 30.0,
) -> Path:
    """Return a path to WAV audio for `text`, fetching only on a cache miss."""
    if not text.strip():
        raise ValueError("nothing to synthesize")
    if speaker not in VOICES:
        raise ValueError(f"unknown voice {speaker!r}; choose from {', '.join(VOICES)}")

    path = cache_path(text, speaker, speed, cache_dir)
    if path.exists() and path.stat().st_size > 0:
        return path

    req = urllib.request.Request(
        TARTUNLP_TTS,
        data=json.dumps({"text": text, "speaker": speaker, "speed": speed}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        audio = resp.read()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return path


def available(timeout: float = PROVIDER_TIMEOUT) -> bool:
    """Cheap health check against the config endpoint."""
    try:
        with urllib.request.urlopen(TARTUNLP_TTS, timeout=timeout) as resp:
            return bool(json.loads(resp.read()).get("speakers"))
    except Exception:
        return False
