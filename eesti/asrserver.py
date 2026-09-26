"""The home speech service: a TalTech Estonian recogniser on an always-on Mac,
reached by the Worker through a Cloudflare Tunnel.

Two engines, by what the Mac can run (both measured on the owner's voice at 7%
WER against Workers AI's 36%, docs/asr-evaluation.md):

| Mac | Engine | Set |
|---|---|---|
| Apple silicon | Voxtral Realtime, GPU (`eesti/evals/asr_voxtral.py`) | `VOXTRAL_RT_MODEL` |
| Intel (e.g. Mac mini 2018) | Whisper large-v3-turbo et-verbatim, CPU int8 (`eesti/evals/asr_reference.py`) | `ASR_REFERENCE_MODEL` |

No free host can run a 4B speech model, but the owner's Mac mini can. This is
the smallest service that lets the deployed app use it:

    GET  /health       {"ok", "engine", "loaded"} -- no secret, no audio
    POST /transcribe   audio body -> {"text", "engine"}; needs `x-home-asr-token`

It decides nothing: the Worker hands the words to the app, which grades them,
exactly as it does Workers AI's. The model is loaded once at start-up, so a
recording is answered in seconds rather than after a 20-second load. Audio is
held in memory for one request and never written to disk.

Run: `python -m eesti.cli asr-serve` (launchd starts it at boot;
`deploy/home-asr/install.sh`). It listens on 127.0.0.1 only: the tunnel is the
one way in.
"""

from __future__ import annotations

import hmac
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from starlette.concurrency import run_in_threadpool

MAX_BYTES = 12_000_000

_state = {"loaded": False, "error": ""}
#: One recording at a time: the GPU holds one copy of the model.
_busy = threading.Lock()


def _engine():
    """(name, transcribe, warm-up) for the engine this Mac is set up for."""
    if os.environ.get("VOXTRAL_RT_MODEL"):
        from .evals import asr_voxtral

        return (asr_voxtral.MODEL, asr_voxtral.transcribe,
                lambda: asr_voxtral._load(os.environ["VOXTRAL_RT_MODEL"]))
    if os.environ.get("ASR_REFERENCE_MODEL"):
        from .evals import asr_reference

        return (asr_reference.MODEL, asr_reference.transcribe,
                lambda: asr_reference._load(os.environ["ASR_REFERENCE_MODEL"]))
    return None


def _warm() -> None:
    """Load the model now, so the first learner does not wait for it."""
    try:
        engine = _engine()
        if engine is None:
            raise RuntimeError("set VOXTRAL_RT_MODEL or ASR_REFERENCE_MODEL")
        engine[2]()
        _state["loaded"] = True
    except Exception as exc:  # noqa: BLE001 - reported by /health, not raised
        _state["error"] = f"{type(exc).__name__}: {exc}"[:300]


@asynccontextmanager
async def _lifespan(_app):
    threading.Thread(target=_warm, daemon=True).start()
    yield


app = FastAPI(title="eesti home speech", docs_url=None, redoc_url=None,
              openapi_url=None, lifespan=_lifespan)


@app.get("/health")
def health() -> dict:
    engine = _engine()
    return {"ok": _state["loaded"], "engine": engine[0] if engine else "",
            "loaded": _state["loaded"], "error": _state["error"]}


@app.post("/transcribe")
async def transcribe(request: Request) -> dict:
    expected = os.environ.get("HOME_ASR_TOKEN", "")
    given = request.headers.get("x-home-asr-token", "")
    # No token configured is a refusal, not an open door.
    if not expected or not hmac.compare_digest(given, expected):
        raise HTTPException(status_code=403, detail="forbidden")
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="no audio")
    if len(audio) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="recording too long")
    engine = _engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="no engine configured")

    def run():
        with _busy:
            return engine[1](audio)

    got = await run_in_threadpool(run)
    if got is None:
        raise HTTPException(status_code=503, detail="no engine configured")
    return {"text": got.text, "engine": got.engine}
