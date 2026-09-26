"""The FSRS queue: what is due, what was got wrong, and what it is worth.

Grading keeps the schedule and refreshes the text — the schedule is a fact
about the learner and must survive a re-encounter; the prompt and answer are
renderings of what the app currently knows.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import evs, mining, review
from .deps import db, review_db
from .render import _glosses_for, _topic_name

router = APIRouter()

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
    # The learner's own rating: again | hard | good | easy. For recall cards.
    rating: str | None = None
    # A typed answer instead: code grades it and chooses the rating.
    given: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)


@router.get("/api/review")
def review_queue(limit: int = 20, kind: str | None = None) -> dict:
    """Items due for review, most overdue first."""
    items = review.due(review_db(), limit=limit, kind=kind)
    return {
        "items": [
            {
                "id": i.id, "kind": i.kind, "kind_et": _topic_name(i.kind),
                "lemma": i.lemma,
                "prompt": i.prompt, "answer": i.answer,
                "distractor": i.distractor, "why_ru": i.why_ru,
                "context": i.context, "reps": i.reps, "lapses": i.lapses,
                # A meaning card shows the word in use: an EVS phrase with its
                # Russian, a different one each time it comes back.
                "phrase": (evs.practice_phrase(db(), i.lemma, i.reps)
                           if i.kind == "vocab" else None),
            }
            for i in items
        ],
        # Glosses from the local store only: the queue brings the same words back, but a
        # live lookup per item would be a batch request.
        "glosses": _glosses_for([i.lemma for i in items]),
    }


@router.post("/api/review")
def review_add(req: ReviewAdd) -> dict:
    """Queue an item. Re-adding an existing one keeps its existing schedule."""
    item_id = review.add(
        review_db(), kind=req.kind, lemma=req.lemma, prompt=req.prompt,
        answer=req.answer, tag=req.tag, distractor=req.distractor,
        why_ru=req.why_ru, source=req.source, context=req.context,
    )
    return {"id": item_id}


@router.post("/api/review/grade")
def review_grade(req: ReviewGrade) -> dict:
    """Reschedule a card: from a typed answer graded by code (`given`), or from
    the learner's own rating (`rating`) where there is nothing to type."""
    if (req.given is None) == (req.rating is None):
        raise HTTPException(status_code=400, detail="Нужен либо ответ (given), "
                            "либо оценка (rating), но не оба сразу.")
    try:
        if req.given is not None:
            return review.answer(review_db(), req.id, req.given, req.latency_ms)
        return review.grade(review_db(), req.id, req.rating)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown item") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class MineRequest(BaseModel):
    word: str
    context: str | None = None


@router.post("/api/mine")
def mine(req: MineRequest) -> dict:
    """Queue the grammar pattern behind a word met while reading; refusals carry a
    reason.
    """
    result = mining.from_reading(review_db(), req.word, context=req.context)
    return {"queued": result.queued, "reason": result.reason,
            "id": result.item_id, "kind": result.kind}


@router.get("/api/review/stats")
def review_stats() -> dict:
    """Queue size, and the words that keep coming back wrong, with topic names
    resolved (`kind_et`).
    """
    body = review.stats(review_db())
    for row in body.get("struggling", []):
        row["kind_et"] = _topic_name(row.get("kind"))
    return body
