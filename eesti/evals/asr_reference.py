"""Optional CPU reference for eval only; never imported by the production chain.

Point ASR_REFERENCE_MODEL at TalTech's downloaded ct2 directory. No implicit
network downloads. faster-whisper/PyAV decode browser recordings directly.
"""
from __future__ import annotations

import hashlib
import io
import os
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

MODEL = "TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604"


def _fingerprint(path: Path) -> str:
    """Include decoding assets: identical weights can use different tokenizers."""
    digest = hashlib.sha256()
    for name in ("model.bin", "config.json", "tokenizer.json", "preprocessor_config.json"):
        digest.update(name.encode())
        with (path / name).open("rb") as artifact:
            digest.update(hashlib.file_digest(artifact, "sha256").digest())
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _load(folder: str):
    from faster_whisper import WhisperModel

    path = Path(folder)
    if not path.is_dir():
        raise ValueError("ASR_REFERENCE_MODEL must be a local CTranslate2 directory")
    digest = _fingerprint(path)
    identity = (f"faster-whisper/{version('faster-whisper')} "
                f"ctranslate2/{version('ctranslate2')} "
                f"cpu/int8 beam=5 temperature=0 artifacts-sha256:{digest}")
    return WhisperModel(str(path), device="cpu", compute_type="int8",
                        cpu_threads=os.cpu_count() or 4, local_files_only=True), identity


def transcribe(audio: bytes):
    from ..providers.asr import Transcript

    folder = os.environ.get("ASR_REFERENCE_MODEL")
    if not folder:
        return None
    model, identity = _load(folder)
    segments, _ = model.transcribe(io.BytesIO(audio), language="et", task="transcribe",
                                   vad_filter=True, condition_on_previous_text=False,
                                   beam_size=5, temperature=0.0)
    return Transcript(" ".join(s.text.strip() for s in segments).strip(),
                      identity)
