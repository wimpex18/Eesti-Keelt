"""Local single-user web app. No auth, no deployment, no cloud state.

Run with:  python -m eesti.cli serve
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .config import LEVELS
from .drills import TEMPLATES, generate, generate_verb_drills
from .lookup import annotate, lookup
from .providers import grammar
from .providers import tts
from . import review
from .sources import connect as content_connect
from .sources import query as content_query
from .wordlist import connect

CONTENT_DB = "data/content.db"
REVIEW_DB = "data/review.db"


def review_db():
    return review.connect(REVIEW_DB)

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
        # verb-form is a different generator: it drills irregular stems rather
        # than object case, so it does not share the template pool.
        if req.rules == ["verb-form"]:
            items = generate_verb_drills(
                db(), count=req.count, levels=tuple(req.levels), seed=req.seed
            )
        else:
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


@app.get("/api/library")
def library(skill: str = "lugemine", level: str | None = None, limit: int = 60) -> dict:
    """Harvested study material.

    `public_only` is deliberately NOT exposed as a parameter. This server is the
    single-user local one; the public deployment sets it, and making it a query
    parameter would let a caller ask for owner-only material by guessing.
    """
    conn = content_connect(CONTENT_DB)
    rows = content_query(conn, skill=skill, level=level, limit=limit)
    return {
        "items": [
            {
                "id": r["id"],
                "title": r["title"],
                "level": r["level"],
                "source": r["source_name"],
                "licence": r["licence"],
                "audio_url": r["audio_url"],
                "words": len(( r["body"] or "").split()),
            }
            for r in rows
        ]
    }


@app.get("/api/library/{item_id}")
def library_item(item_id: str) -> dict:
    """One item with its full text and a vocabulary profile."""
    conn = content_connect(CONTENT_DB)
    row = conn.execute(
        """SELECT i.*, s.name AS source_name, s.licence
           FROM items i JOIN sources s ON s.id = i.source_id
           WHERE i.id = ?""",
        (item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": row["id"],
        "title": row["title"],
        "body": row["body"],
        "level": row["level"],
        "source": row["source_name"],
        "licence": row["licence"],
        "audio_url": row["audio_url"],
        "profile": annotate(row["body"] or ""),
    }


@app.get("/api/lookup/{word}")
def lookup_word(word: str) -> dict:
    """Analyse one word: lemma, case, CEFR level, and its object-case pair."""
    return lookup(word)


class ReviewAdd(BaseModel):
    kind: str
    lemma: str
    prompt: str
    answer: str
    tag: str | None = None
    distractor: str | None = None
    why_ru: str | None = None
    source: str = "drill"
    context: str | None = None


class ReviewGrade(BaseModel):
    id: str
    rating: str  # again | hard | good | easy


@app.get("/api/review")
def review_queue(limit: int = 20, kind: str | None = None) -> dict:
    """Items due for review, most overdue first."""
    items = review.due(review_db(), limit=limit, kind=kind)
    return {
        "items": [
            {
                "id": i.id, "kind": i.kind, "lemma": i.lemma,
                "prompt": i.prompt, "answer": i.answer,
                "distractor": i.distractor, "why_ru": i.why_ru,
                "context": i.context, "reps": i.reps, "lapses": i.lapses,
            }
            for i in items
        ]
    }


@app.post("/api/review")
def review_add(req: ReviewAdd) -> dict:
    """Queue an item. Re-adding an existing one keeps its existing schedule."""
    item_id = review.add(
        review_db(), kind=req.kind, lemma=req.lemma, prompt=req.prompt,
        answer=req.answer, tag=req.tag, distractor=req.distractor,
        why_ru=req.why_ru, source=req.source, context=req.context,
    )
    return {"id": item_id}


@app.post("/api/review/grade")
def review_grade(req: ReviewGrade) -> dict:
    try:
        return review.grade(review_db(), req.id, req.rating)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown item") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/review/stats")
def review_stats() -> dict:
    return review.stats(review_db())


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
