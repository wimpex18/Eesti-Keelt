"""The FSRS queue: what is due, what was got wrong, and what it is worth.

Grading keeps the schedule and refreshes the text — the schedule is a fact
about the learner and must survive a re-encounter; the prompt and answer are
renderings of what the app currently knows.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import mining, review
from .deps import review_db
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
    rating: str  # again | hard | good | easy


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
            }
            for i in items
        ],
        # The queue is where the same words come back by design, so it is the
        # place a missing meaning compounds: an item can be answered correctly
        # from the form alone, review after review, without the word ever
        # meaning anything. Local store only -- twenty items would be twenty
        # live lookups.
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
    try:
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
    """Queue the grammar pattern behind a word met while reading.

    Refusals carry a reason, so the reader can explain why a word was not added
    rather than appearing to do nothing.
    """
    result = mining.from_reading(review_db(), req.word, context=req.context)
    return {"queued": result.queued, "reason": result.reason,
            "id": result.item_id, "kind": result.kind}


@router.get("/api/review/stats")
def review_stats() -> dict:
    """Queue size, and the words that keep coming back wrong.

    `kind` is a topic id. `/api/review` has sent `kind_et` beside every item
    since it was written, for the documented reason that a page which turns ids
    into names will eventually meet an id nobody taught it about -- and this
    endpoint sent the bare id, so the struggling list showed `osastav` where
    the topic is called `osastav kääne`. Resolved here, beside the other one.
    """
    body = review.stats(review_db())
    for row in body.get("struggling", []):
        row["kind_et"] = _topic_name(row.get("kind"))
    return body
