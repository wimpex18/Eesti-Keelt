"""The state snapshot, and the reset.

Cloud Run disk is ephemeral and scales to zero, so the Worker exports and
re-imports the learner's databases around cold starts. Paths come from `config`
at call time.
"""

from __future__ import annotations

import base64
import hmac
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .deps import progress_db

router = APIRouter()

# --------------------------------------------------------------------------
# State snapshots
# --------------------------------------------------------------------------
#
# The durable copy lives in the Worker's Durable Object; these endpoints move it
# in and out. Only the learner's databases travel — the word list, form index and
# corpus are baked into the image or pushed separately.

STATE_DATABASES = ("progress", "review", "vocab")


def _state_paths() -> dict[str, Path]:
    """Every database the snapshot carries, resolved from `config` when asked."""
    from .. import config

    return {
        "progress": Path(config.PROGRESS_DB),
        "review": Path(config.REVIEW_DB),
        "vocab": Path(config.VOCAB_DB),
        # Queued corrections are learner data and travel too.
        "notion": Path(config.NOTION_DB),
    }


def _require_state_token(request: Request) -> None:
    """Snapshots are for the platform, not the browser: they require `STATE_TOKEN`, and
    refuse outright when it is unset.
    """
    expected = os.environ.get("STATE_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="STATE_TOKEN is not configured")
    if not hmac.compare_digest(request.headers.get("x-state-token", ""), expected):
        raise HTTPException(status_code=403, detail="bad state token")


class ResetRequest(BaseModel):
    topic: str | None = None
    everything: bool = False


@router.post("/api/progress/reset")
def progress_reset(req: ResetRequest, request: Request) -> dict:
    """Forget a topic's attempts (operator action, guarded by `STATE_TOKEN`).

    A missing `topic` is refused unless `everything` is set explicitly.
    """
    _require_state_token(request)
    from ..progress import reset

    if not req.topic and not req.everything:
        raise HTTPException(
            status_code=400,
            detail="Pass a topic, or everything=true to clear all of it.",
        )
    return reset(progress_db(), req.topic)


@router.get("/api/state/export")
def state_export(request: Request) -> dict:
    """The learner's databases, base64'd, for the Worker to persist."""
    _require_state_token(request)
    out = {}
    for name, path in _state_paths().items():
        out[name] = (
            base64.b64encode(path.read_bytes()).decode("ascii")
            if path.exists() else ""
        )
    return {"databases": out, "bytes": sum(len(v) for v in out.values())}


class StateBlob(BaseModel):
    databases: dict[str, str]


# The table that means "this learner has done something" in each database; a
# file with only its schema does not count.
LEARNER_ROWS = {
    "progress": "attempts",
    "review": "review_items",
    "vocab": "vocab_status",
    "notion": "notion_queue",
}


def _has_learner_data(path: Path, table: str) -> bool:
    """True only if there are learner rows worth protecting, not just a schema."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > 0
    except sqlite3.Error:
        # Unreadable or not a database: not something worth preserving, but not
        # something to overwrite blindly either.
        return True


class ContentBlob(BaseModel):
    database: str = Field(min_length=1)


@router.post("/api/content/import")
def content_import(blob: ContentBlob, request: Request) -> dict:
    """Receive the harvested library, which cannot ship in the image.

    The corpus is owner-only and Cloud Run's disk is ephemeral, so the Worker holds
    it and pushes it into each fresh instance. Unlike the learner snapshot this
    overwrites: the corpus is derived, so there is no learner work to lose.
    """
    _require_state_token(request)
    from .. import config

    path = Path(config.CONTENT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(blob.database))

    from ..sources import connect as _connect

    with _connect(path) as conn:
        items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    return {"bytes": path.stat().st_size, "items": items}


@router.get("/api/content/export")
def content_export(request: Request) -> dict:
    """Hand the library back so the Worker can archive it (a script cannot pass
    Access, so pushes go to the origin). `full` returns the file; otherwise just
    presence and size.
    """
    _require_state_token(request)
    from .. import config
    from ..sources import available

    path = Path(config.CONTENT_DB)
    present = available(path)
    out = {
        "present": present,
        "bytes": path.stat().st_size if path.exists() else 0,
    }
    if present and request.query_params.get("full"):
        out["database"] = base64.b64encode(path.read_bytes()).decode("ascii")
    return out


@router.post("/api/state/import")
def state_import(blob: StateBlob, request: Request) -> dict:
    """Restore a snapshot into a fresh container.

    Refuses to overwrite a database that already holds learner rows (newer work
    wins); an empty schema is overwritten.
    """
    _require_state_token(request)
    restored, skipped = [], []
    for name, path in _state_paths().items():
        payload = blob.databases.get(name) or ""
        if not payload:
            continue
        if _has_learner_data(path, LEARNER_ROWS[name]):
            skipped.append(name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(payload))
        restored.append(name)

    # After a restore, run the idempotent repair of fabricated placement attempts;
    # at import it would clean a database the restore is about to replace.
    repair = None
    if "progress" in restored:
        from ..progress import connect as progress_connect
        from ..progress import repair_fabricated_attempts

        # `_state_paths()` rather than a second way of naming the same file:
        # its own docstring is about exactly that, and it resolves at call time.
        repair = repair_fabricated_attempts(
            progress_connect(_state_paths()["progress"]))
    return {"restored": restored, "skipped": skipped, "repair": repair}
