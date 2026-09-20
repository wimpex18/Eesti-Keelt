"""Am I ready: official material, the verdict, and the mixed checkpoint.

The verdict reports four exam parts separately and never as one total, and it
says in Russian that it is not a prediction — a caveat nobody can read is not
a caveat.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..config import LEVELS
from .deps import content_db, db, notion_db, progress_db, vocab_db
from .render import _glosses_for, item_for_page

router = APIRouter()

@router.get("/api/exam/{level}")
def exam(level: str) -> dict:
    """The whole exam section for one level, in one request."""
    from ..library import exam_material

    if level not in LEVELS + ("B2", "C1"):
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    return exam_material(content_db(), level)


@router.get("/api/readiness/{level}")
def exam_readiness(level: str) -> dict:
    """Evidence for and against sitting a level. Not a prediction: every part is
    reported separately, since any part at zero fails.
    """
    from ..readiness import readiness

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")

    return readiness(
        level, progress=progress_db(), vocabulary=vocab_db(), words=db(),
        content=content_db(), notion=notion_db(),
    ).to_dict()


@router.get("/api/checkpoint/{level}")
def checkpoint_items(level: str, count: int = 15, seed: int | None = None) -> dict:
    """A mixed set across a whole level — interleaved by construction."""
    import secrets

    from ..checkpoint import PASS_MARK, build, ready, topics_at
    from ..itemref import checkpoint_ref, sign

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    seed = seed if seed is not None else secrets.randbelow(2**31)
    items = build(level, count=count, seed=seed)
    return {
        "level": level,
        "ready": ready(progress_db(), level),
        "pass_mark": PASS_MARK,
        "topics": topics_at(level),
        "items": [
            item_for_page(i) | {"token": sign(i, checkpoint_ref(
                level, seed=seed, count=count, index=n))}
            for n, i in enumerate(items)
        ],
        # Glosses for the checkpoint's words from the local store only, never a live
        # lookup per item.
        "glosses": _glosses_for([i.lemma for i in items]),
    }


class CheckpointResult(BaseModel):
    asked: int = Field(ge=1, le=30)
    correct: int = Field(ge=0)


@router.post("/api/checkpoint/{level}/result")
def checkpoint_result(level: str, res: CheckpointResult) -> dict:
    """Record a finished checkpoint taken on the page.

    Each answer was already graded and recorded by `/api/practice/answer`; this
    closes the set, so readiness can see that a level's checkpoint was passed. The
    tally comes from the page, as the items do (see the note in `eesti/app.py`).
    """
    from ..checkpoint import PASS_MARK, save

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    if res.correct > res.asked:
        raise HTTPException(status_code=400, detail="correct exceeds asked")
    passed = save(progress_db(), level, res.asked, res.correct)
    return {"level": level, "passed": passed, "pass_mark": PASS_MARK}


# --------------------------------------------------------------------------
# The exam itself: its shape, its sittings, and the one being prepared for
# --------------------------------------------------------------------------

@router.get("/api/exam-spec/{level}")
def exam_spec(level: str) -> dict:
    """What the exam is: parts, minutes, points and the pass rule (`eesti/exam.py`)."""
    from ..exam import NEXT_YEAR, SPECS, upcoming

    if level not in SPECS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    return SPECS[level].to_dict() | {
        "sessions": [s.to_dict() for s in upcoming(level)],
        "next_year": NEXT_YEAR,
    }


class GoalRequest(BaseModel):
    level: str
    #: The sitting, `YYYY-MM-DD`; null keeps the level with no date yet.
    sitting: str | None = None


@router.get("/api/goal")
def read_goal() -> dict:
    """The sitting being prepared for, or null."""
    from ..exam import goal

    chosen = goal(progress_db())
    return {"goal": chosen.to_dict() if chosen else None}


@router.post("/api/goal")
def choose_goal(req: GoalRequest) -> dict:
    """Choose the sitting to prepare for. The countdown follows it."""
    from datetime import date

    from ..exam import set_goal

    try:
        when = date.fromisoformat(req.sitting) if req.sitting else None
    except ValueError as exc:
        raise HTTPException(status_code=400,
                            detail="Дата экзамена — в виде ГГГГ-ММ-ДД.") from exc
    try:
        chosen = set_goal(progress_db(), req.level, when)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"goal": chosen.to_dict()}


@router.get("/api/goal.ics")
def goal_calendar() -> PlainTextResponse:
    """The sitting and its registration deadline, for a calendar app."""
    from ..exam import calendar, goal

    chosen = goal(progress_db())
    if chosen is None or not (chosen.sitting or chosen.registration_closes):
        raise HTTPException(status_code=404, detail="Сессия ещё не выбрана.")
    return PlainTextResponse(
        calendar(chosen), media_type="text/calendar",
        headers={"content-disposition": 'attachment; filename="eesti-keelt-eksam.ics"'})
