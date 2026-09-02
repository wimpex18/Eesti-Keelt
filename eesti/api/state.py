"""The state snapshot, and the reset.

Cloud Run scales to zero and gives no shutdown hook, so the learner's four
databases are exported and re-imported by the Worker around a cold start. Every
path here comes from `config` at call time, and so do the database helpers —
they used to be two sets that could drift, and a restore could land in a file
the app never opened.
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
# State snapshots — the thing that stops a deploy eating the learner's progress
# --------------------------------------------------------------------------
#
# Cloudflare Containers have **ephemeral disk**: "when a Container instance goes
# to sleep, the next time it is started, it will have a fresh disk as defined by
# its container image." With a ten-minute sleep timer, that means every coffee
# break would reset mastery, the review queue and the vocabulary table — the
# state that steps 3 to 9 exist to accumulate.
#
# So the durable copy lives outside the container, in the Durable Object that
# manages it, and these two endpoints are how it gets in and out. Only the
# *learner's* databases travel: the word list, the form index and the harvested
# corpus are derived or baked into the image, so shipping them would be copying
# 58 MB to say nothing.

STATE_DATABASES = ("progress", "review", "vocab")


def _state_paths() -> dict[str, Path]:
    """Every database the snapshot carries, resolved when asked.

    Read from `config` rather than from this module's own copies. The copies
    are bound at import, so redirecting the databases meant patching them in
    two places -- `config` for the CLI and `app` for the web application -- and
    the test suite carries a comment saying exactly that. One source, read at
    call time, is the same correction already applied to the circuit breaker.
    """
    from .. import config

    return {
        "progress": Path(config.PROGRESS_DB),
        "review": Path(config.REVIEW_DB),
        "vocab": Path(config.VOCAB_DB),
        # Queued corrections are learner data like any other. Leaving this out
        # meant every error waiting for review evaporated on the next cold
        # start -- and Cloud Run cold-starts after minutes of idling, so a queue
        # whose whole purpose is to hold things until a person looks at them
        # held nothing across a coffee break.
        "notion": Path(config.NOTION_DB),
    }


def _require_state_token(request: Request) -> None:
    """Snapshots are for the platform, not for the browser.

    Cloudflare Access already gates the whole app, but a restore endpoint
    overwrites everything the learner has done, so it does not rely on a single
    layer. With no token configured the endpoints refuse outright rather than
    defaulting to open — an unset secret is a misconfiguration, not permission.
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
    """Forget a topic's attempts.

    Guarded by `STATE_TOKEN` rather than left open behind Access, for the same
    reason the snapshot endpoints are: this destroys learner history, and a
    misfired request from a page the learner has open should not be able to do
    that. It is an operator action, not a UI button.

    Clearing everything must be asked for explicitly. A missing `topic` is far
    more likely to be a bug in a caller than a genuine wish to erase months of
    work, so it is refused unless `everything` says otherwise.
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


# The table that means "this learner has actually done something" in each
# database. Existence of the file is not that: the first request to arrive
# creates it *with its schema*, so "the file is non-empty" is true of a
# completely fresh container.
LEARNER_ROWS = {
    "progress": "attempts",
    "review": "review_items",
    "vocab": "vocab_status",
    "notion": "notion_queue",
}


def _has_learner_data(path: Path, table: str) -> bool:
    """True only if there is real work in there worth protecting.

    Tested against a live container, which is how the bug this replaces was
    found: a fresh instance answered `/api/curriculum`, which created
    `progress.db` with an empty schema, and the restore that followed refused to
    overwrite it — silently discarding the snapshot it existed to restore.
    """
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

    Two facts collide here. The corpus is **owner-only** -- ERR transcripts are
    © ERR, Selges keeles carries no reuse grant -- so it has no business inside
    an image built from a public repository. And Cloud Run's disk is
    **ephemeral**, so a file copied in by hand is gone at the next cold start.

    So it travels the same road the learner's progress does: held by the Worker,
    pushed in whenever a fresh instance appears. Harvest once on a laptop, push
    once, and every container after that gets it without the harvest ever
    running again -- which also keeps this app from re-scraping someone else's
    server on every deploy.

    Unlike the learner snapshot, this one **does** overwrite. The corpus is
    derived from a harvest, not accumulated by the learner: there is no work in
    it to lose, and refusing would make re-harvesting impossible.
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
    """Hand the library back, so the Worker can archive what was pushed here.

    Cloudflare Access guards the Worker, and Access is an interactive login: a
    script cannot satisfy it. So a harvest is pushed to *this* origin, which is
    guarded by `PROXY_TOKEN` and reachable by a machine -- and the Worker picks
    it up from here and keeps it, because this disk will not exist tomorrow.

    `full` is opt-in because the answer is megabytes. Without it this is a
    cheap "is there one, and how big", which is all the Worker needs to decide
    whether to ask for the expensive version.
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

    Refuses to overwrite a database that already holds **learner rows** — not
    merely one that exists. A restore racing a learner who has started answering
    would discard the newer work, and losing five minutes beats losing it
    silently; but an empty schema is not work, and treating it as such made the
    restore refuse every time, which is the failure the snapshot exists to
    prevent.
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

    # A restore is the only moment this container's learner record exists and
    # is the real one, so it is the only place a repair to that record can run.
    #
    # `cli placement` used to write `PROBE_ITEMS` blank wrong attempts whenever
    # nobody was answering. That is fixed, and the fix cannot reach rows already
    # in a snapshot -- on a deployment nobody working on this repository can
    # read, the record may still say the learner failed drills they never saw.
    # Running it here needs no operator: Cloud Run scales to zero, every cold
    # start restores, and the repair is idempotent by name and rides the next
    # snapshot so it is not repeated.
    #
    # At import time instead of here would clean a database the restore is
    # about to overwrite.
    repair = None
    if "progress" in restored:
        from ..progress import connect as progress_connect
        from ..progress import repair_fabricated_attempts

        # `_state_paths()` rather than a second way of naming the same file:
        # its own docstring is about exactly that, and it resolves at call time.
        repair = repair_fabricated_attempts(
            progress_connect(_state_paths()["progress"]))
    return {"restored": restored, "skipped": skipped, "repair": repair}
