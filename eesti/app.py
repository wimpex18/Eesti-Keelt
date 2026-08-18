"""Local single-user web app. No auth, no deployment, no cloud state.

Run with:  python -m eesti.cli serve
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .config import LEVELS
from .drills import TEMPLATES, generate
from .providers import grammar
from .providers import tts
from .wordlist import connect

WEB = Path(__file__).parent / "web"

app = FastAPI(title="Eesti-Keelt", docs_url="/api/docs")


def db():
    return connect()


class CheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class DrillRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=50)
    levels: list[str] = Field(default_factory=lambda: list(LEVELS))
    rules: list[str] | None = None
    seed: int | None = None


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str = tts.DEFAULT_VOICE
    speed: float = Field(default=tts.LEARNER_SPEED, ge=0.5, le=2.0)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (WEB / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict:
    conn = db()
    words = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    drillable = conn.execute(
        "SELECT COUNT(*) FROM object_cases WHERE distinct_=1"
    ).fetchone()[0]
    return {
        "words": words,
        "drillable_nouns": drillable,
        "rules": sorted({t.rule for t in TEMPLATES}),
        "voices": list(tts.VOICES),
    }


@app.post("/api/check")
def check(req: CheckRequest) -> dict:
    """Grammar check through the provider chain."""
    return grammar.check(req.text).to_dict()


@app.post("/api/drills")
def drills(req: DrillRequest) -> dict:
    """Generate object-case drills. Fully offline."""
    try:
        items = generate(
            db(),
            count=req.count,
            levels=tuple(req.levels),
            rules=tuple(req.rules) if req.rules else None,
            seed=req.seed,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"drills": [d.to_dict() for d in items]}


@app.post("/api/speak")
def speak(req: SpeakRequest) -> FileResponse:
    """Synthesize Estonian audio for arbitrary text — turns anything into listening practice."""
    try:
        path = tts.synthesize(req.text, speaker=req.voice, speed=req.speed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"TTS unavailable: {type(exc).__name__}"
        ) from exc
    return FileResponse(path, media_type="audio/wav", filename="eesti.wav")
