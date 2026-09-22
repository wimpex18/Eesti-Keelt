"""Optional CPU reference for eval only; never imported by the production chain.

Point ASR_REFERENCE_MODEL at TalTech's downloaded ct2 directory. No implicit
network downloads. faster-whisper/PyAV decode browser recordings directly.
"""
from __future__ import annotations

import hashlib
import io
import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _load(folder: str):
    from faster_whisper import WhisperModel

    path = Path(folder)
    if not path.is_dir():
        raise ValueError("ASR_REFERENCE_MODEL must be a local CTranslate2 directory")
    with (path / "model.bin").open("rb") as weights:
        digest = hashlib.file_digest(weights, "sha256").hexdigest()
    return WhisperModel(str(path), device="cpu", compute_type="int8",
                        local_files_only=True), digest


def transcribe(audio: bytes):
    from ..providers.asr import Transcript

    folder = os.environ.get("ASR_REFERENCE_MODEL")
    if not folder:
        return None
    model, digest = _load(folder)
    segments, _ = model.transcribe(io.BytesIO(audio), language="et", task="transcribe",
                                   vad_filter=True, condition_on_previous_text=False,
                                   beam_size=5)
    return Transcript(" ".join(s.text.strip() for s in segments).strip(),
                      f"faster-whisper cpu/int8 beam=5 model-sha256:{digest}")
