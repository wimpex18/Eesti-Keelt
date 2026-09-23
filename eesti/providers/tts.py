"""Estonian speech synthesis via TartuNLP's public TTS API (no client key).

Makes listening possible from any text. Output is cached on disk by content
hash; on Cloud Run that disk is ephemeral, so the cache lasts a container's
lifetime — a latency cost, not worth storing audio in the state snapshot.
"""

from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import urllib.request
from pathlib import Path

from .. import config

# Supported app voices, a subset of the live catalogue. "mari" is the default.
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
        f"{speaker}|{speed}|{text}".encode()
    ).hexdigest()[:20]
    return Path(cache_dir or config.CACHE) / "audio" / f"{digest}.wav"


def valid_wav(audio: bytes) -> bool:
    """Reject error pages and incomplete downloads, including cached ones.

    The live service returns IEEE-float WAV, unsupported by Python's wave
    reader. Validate RIFF chunks without converting or altering the audio.
    """
    if len(audio) < 12 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        return False
    if int.from_bytes(audio[4:8], "little") + 8 != len(audio):
        return False
    offset, frame_size, data_size = 12, 0, 0
    while offset + 8 <= len(audio):
        name = audio[offset:offset + 4]
        size = int.from_bytes(audio[offset + 4:offset + 8], "little")
        start = offset + 8
        if start + size > len(audio):
            return False
        if name == b"fmt ":
            if size < 16:
                return False
            encoding, channels, rate, byte_rate, align, bits = struct.unpack_from(
                "<HHIIHH", audio, start)
            if (encoding not in (1, 3) or not channels or not rate or not bits
                    or bits % 8 or align != channels * (bits // 8)
                    or byte_rate != rate * align):
                return False
            frame_size = align
        elif name == b"data":
            data_size += size
        offset = start + size + size % 2
    return offset == len(audio) and bool(frame_size and data_size and data_size % frame_size == 0)


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
    if not 0.5 <= speed <= 2.0:
        raise ValueError("speed must be between 0.5 and 2.0")

    path = cache_path(text, speaker, speed, cache_dir)
    if path.exists() and valid_wav(path.read_bytes()):
        return path

    req = urllib.request.Request(
        config.TARTUNLP_TTS,
        data=json.dumps({"text": text, "speaker": speaker, "speed": speed}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        audio = resp.read()
    if not valid_wav(audio):
        raise OSError("speech provider returned invalid WAV audio")

    path.parent.mkdir(parents=True, exist_ok=True)
    # Concurrent requests must never see a partially written cache entry.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as pending:
            temporary = Path(pending.name)
            pending.write(audio)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def available(timeout: float | None = None) -> bool:
    """Cheap health check against the config endpoint."""
    try:
        with urllib.request.urlopen(config.TARTUNLP_TTS, timeout=timeout or config.PROVIDER_TIMEOUT) as resp:
            payload = json.loads(resp.read())
        return isinstance(payload, dict) and any(
            isinstance(speaker, dict) and speaker.get("name") == DEFAULT_VOICE
            for speaker in (payload.get("speakers") or [])
        )
    except (OSError, ValueError, TypeError):
        return False
