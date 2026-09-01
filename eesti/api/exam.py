"""Am I ready: official material, the verdict, and the mixed checkpoint.

The verdict reports four exam parts separately and never as one total, and it
says in Russian that it is not a prediction — a caveat nobody can read is not
a caveat.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import LEVELS
from .deps import content_db, db, notion_db, progress_db, vocab_db
from .render import _glosses_for

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
    """Evidence for and against sitting a level, with the reasons named.

    Not a prediction. The pass rule is 60% overall *and* no part at zero, so
    this reports every part separately — an aggregate would hide the untouched
    part that is the actual risk.
    """
    from ..readiness import readiness

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    from ..notion import connect as notion_connect

    return readiness(
        level, progress=progress_db(), vocabulary=vocab_db(), words=db(),
        content=content_db(), notion=notion_db(),
    ).to_dict()


@router.get("/api/checkpoint/{level}")
def checkpoint_items(level: str, count: int = 15, seed: int | None = None) -> dict:
    """A mixed set across a whole level — interleaved by construction."""
    from ..checkpoint import PASS_MARK, build, ready, topics_at

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    items = build(level, count=count, seed=seed)
    return {
        "level": level,
        "ready": ready(progress_db(), level),
        "pass_mark": PASS_MARK,
        "topics": topics_at(level),
        "items": [i.to_dict() for i in items],
        # What the words in this set mean, from the local store only.
        #
        # A B1 object-case set comes back on lemmas like `etendus`, `luuletus`
        # and `rahakott`. A learner can inflect those correctly without knowing
        # one of them, and then has practised morphology on a token -- which is
        # half of what the exercise looks like it is teaching.
        #
        # Local reads only: a live lookup per item would be the batch request
        # `sonapi` refuses to have a helper for, and would make a practice set
        # wait on a third party. Words not yet stored are simply not glossed,
        # and get filled one at a time as each item is answered.
        "glosses": _glosses_for([i.lemma for i in items]),
    }
