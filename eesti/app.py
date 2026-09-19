"""The FastAPI application: single learner, served locally (`cli serve`) or on
Cloud Run behind the Cloudflare Worker.

This module is the assembly: the application object, the one piece of
middleware that guards the origin, and the names that the CLI, the tests and
the deployment scripts import from `eesti.app`. Every route lives in
`eesti/api/`, one module per thing the learner is doing.
"""

from __future__ import annotations

import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import api
from .api.deps import (  # noqa: F401  -- re-exported; the tests and CLI read these
    BOOT_ID,
    BUILD,
    PROXY_HEADER,
    WEB,
    build_info,
    content_available,
    content_db,
    db,
    gloss_db,
    notion_db,
    progress_db,
    review_db,
    vocab_db,
)
# Learner database paths are not re-exported here: everything reads
# `eesti.config` at call time, so each file has one name.

# Generated items are not stored: the client returns the item with the answer
# and the server re-grades it. Fine for one learner behind Access; a multi-user
# app would need signed items or server-side sessions.

app = FastAPI(title="Eesti-Keelt", docs_url="/api/docs")


@app.middleware("http")
async def _proxy_guard(request: Request, call_next):
    """Keep the origin from becoming a way around the front door.

    Cloud Run is invoked unauthenticated, so its `run.app` URL is public while
    Access guards only the Worker. With `PROXY_TOKEN` set, every request must carry
    it (only the Worker holds it); unset, as under `cli serve`, the guard is off.
    `/api/health` reports `origin_guarded`.
    """
    expected = os.environ.get("PROXY_TOKEN")
    if expected and not hmac.compare_digest(
        request.headers.get(PROXY_HEADER, ""), expected
    ):
        return JSONResponse({"detail": "not authorised"}, status_code=403)
    response = await call_next(request)
    response.headers["x-boot-id"] = BOOT_ID
    # How far the evidence log has got, so the Worker pulls only when there is
    # something new (`deploy/worker.ts`, `pullEvents`).
    # Only API calls record evidence; the page and its assets never need it.
    if request.url.path.startswith("/api/"):
        seq = _events_seq()
        if seq is not None:
            response.headers["x-events-seq"] = str(seq)
    return response


def _events_seq() -> int | None:
    """The log's last sequence number, read-only and without creating the file."""
    import sqlite3

    from . import config

    path = Path(config.EVENTS_DB)
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = 'events'").fetchone()
        finally:
            conn.close()
        return row[0] if row else 0
    except sqlite3.Error:  # a header is never worth failing a request
        return None


api.register(app)
