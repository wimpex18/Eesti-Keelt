"""The error log: queueing a correction, and sending chosen rows to Notion.

`config.NOTION_DB` is read when the queue is opened, not bound at import.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .deps import notion_db

router = APIRouter()

class QueueError(BaseModel):
    wrong: str = Field(min_length=1, max_length=2000)
    correct: str = Field(min_length=1, max_length=2000)
    why: str = Field(default="", max_length=2000)
    tag: str


@router.post("/api/notion/queue")
def notion_queue(row: QueueError) -> dict:
    """Hold a confirmed error for the Notion log. Queued, never sent.

    The `Vead` log is hand-curated (three rows sharing a tag set the week's focus),
    so nothing is sent without the learner choosing it.
    """
    from ..notion import Row, queue

    try:
        entry = Row(wrong=row.wrong, correct=row.correct, why=row.why, tag=row.tag)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    added = queue(notion_db(), entry)
    return {"queued": added, "tag": entry.tag,
            "note": "Проверь через `cli notion`, отправь `cli notion --push`."}


@router.get("/api/notion/pending")
def notion_pending() -> dict:
    from ..notion import pending

    return {
        "items": [dict(r) for r in pending(notion_db())],
        # Whether pressing "send" can possibly work, said before it is pressed
        # rather than as a failure afterwards.
        "can_push": bool(os.environ.get("NOTION_TOKEN")),
    }


class NotionPush(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=50)


@router.post("/api/notion/push")
def notion_push(req: NotionPush) -> dict:
    """Send named rows to the `Vead` log. Nothing else, ever.

    Takes ids, not "push everything": the page shows the queue and sends the ticked
    rows. A row that fails to send stays queued.
    """
    from ..notion import Row, mark_pushed, pending, push

    if not os.environ.get("NOTION_TOKEN"):
        raise HTTPException(
            status_code=503,
            detail="NOTION_TOKEN is not set on this service, so nothing can "
                   "be sent. The rows stay queued.",
        )

    conn = notion_db()
    by_id = {r["id"]: r for r in pending(conn)}
    sent, failed = [], []
    for row_id in req.ids:
        row = by_id.get(row_id)
        if row is None:
            # Already pushed, or never queued. Not an error worth failing the
            # whole request over, and worth naming so the page can drop it.
            failed.append({"id": row_id, "detail": "not queued"})
            continue
        ok, detail = push(Row(wrong=row["wrong"], correct=row["correct"],
                              why=row["why"], tag=row["tag"]))
        if ok:
            mark_pushed(conn, row_id)
            sent.append(row_id)
        else:
            failed.append({"id": row_id, "detail": detail})
    return {"sent": sent, "failed": failed,
            "remaining": len(pending(conn))}
