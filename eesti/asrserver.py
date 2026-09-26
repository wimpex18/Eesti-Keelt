"""The home speech service: TalTech's Voxtral Realtime on an always-on Mac,
reached by the Worker through a Cloudflare Tunnel.

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


def _warm() -> None:
    """Load the model now, so the first learner does not wait for it."""
    try:
        from .evals.asr_voxtral import _load

        _load(os.environ["VOXTRAL_RT_MODEL"])
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
    from .evals.asr_voxtral import MODEL

    return {"ok": _state["loaded"], "engine": MODEL, "loaded": _state["loaded"],
            "error": _state["error"]}


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
    from .evals.asr_voxtral import transcribe as voxtral_rt

    def run():
        with _busy:
            return voxtral_rt(audio)

    got = await run_in_threadpool(run)
    if got is None:
        raise HTTPException(status_code=503, detail="VOXTRAL_RT_MODEL is not set")
    return {"text": got.text, "engine": got.engine}
