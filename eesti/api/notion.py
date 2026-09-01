"""The error log: queueing a correction, and sending the queue to Notion.

A queue with no drain is not a feature — corrections used to be queueable from
the app and sendable only from a CLI that does not exist on the deployment, so
the queue filled forever and the readiness verdict counted queued rows as
though they had been logged.

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

    The `Vead` log is hand-curated, and its "three of a tag becomes this week's
    focus" rule is what identified `obj-case` as the priority at all. Appending
    every suspicion would turn a picked record into a dump and start that rule
    firing on noise -- so this endpoint only ever queues. `cli notion --push`
    is the one thing that writes, and it shows you the rows first.
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

    This was missing, and its absence was quiet in the worst way. Corrections
    could be queued from the app but pushed only by `cli notion --push` — and
    the CLI does not exist on the deployment: the container is ephemeral and
    the learner is on a phone. So the queue filled and never drained, and the
    readiness verdict counted queued rows as writing evidence, which measured
    the queue rather than the log it is supposed to feed.

    It takes **ids**, not "push everything". The `Vead` log's worth is that it
    is curated — three rows sharing a tag become the focus of the week, and
    that rule is what identified `obj-case` in the first place. An endpoint
    that drained the queue wholesale would be the same mistake as appending
    every suspicion, one step later. The page shows the rows and sends the ones
    ticked.

    A row that fails to send stays queued. The queue is the record until Notion
    says it has one.
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
