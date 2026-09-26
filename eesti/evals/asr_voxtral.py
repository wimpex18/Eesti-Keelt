"""TalTech's Voxtral Realtime Estonian, for eval only; never imported by the
production chain.

`TalTechNLP/Voxtral-Mini-4B-Realtime-estonian-2609` (Apache-2.0, 4B parameters,
8.9 GB in BF16) through Transformers ≥ 5.2 on the owner's machine: Apple GPU
(`mps`) or CUDA when present, CPU otherwise. It transcribes a whole clip, like
the other engines; streaming needs vLLM on a CUDA GPU, which no free host
offers.

Point `VOXTRAL_RT_MODEL` at the downloaded model directory (or its Hub id when
the Hugging Face cache holds it). No implicit network downloads: the model is
loaded with `local_files_only`.
"""
from __future__ import annotations

import os
from functools import lru_cache

MODEL = "TalTechNLP/Voxtral-Mini-4B-Realtime-estonian-2609"


@lru_cache(maxsize=1)
def _load(where: str):
    import torch
    from transformers import AutoProcessor, VoxtralRealtimeForConditionalGeneration

    device = ("mps" if torch.backends.mps.is_available()
              else "cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device != "cpu" else torch.float32
    processor = AutoProcessor.from_pretrained(where, local_files_only=True)
    model = VoxtralRealtimeForConditionalGeneration.from_pretrained(
        where, torch_dtype=dtype, local_files_only=True).to(device).eval()
    return processor, model, device, dtype


def transcribe(audio: bytes):
    """A whole clip, greedy decoding (the model card's `temperature=0`)."""
    from ..providers.asr import Transcript

    where = os.environ.get("VOXTRAL_RT_MODEL")
    if not where:
        return None
    import torch
    from mistral_common.tokens.tokenizers.audio import Audio

    processor, model, device, dtype = _load(where)
    clip = Audio.from_bytes(audio, strict=False)
    clip.resample(processor.feature_extractor.sampling_rate)
    inputs = processor(clip.audio_array, return_tensors="pt").to(device, dtype=dtype)
    with torch.no_grad():
        ids = model.generate(**inputs, do_sample=False, max_new_tokens=256)
    text = processor.batch_decode(ids, skip_special_tokens=True)[0].strip()
    return Transcript(text, f"{MODEL} ({device}, transformers)")
