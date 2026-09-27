"""The FastAPI application: scope-aware learners, served locally (`cli serve`) or on
Cloud Run behind the Cloudflare Worker.

This module is the assembly: the application object, the one piece of
middleware that guards the origin, and the names that the CLI, the tests and
the deployment scripts import from `eesti.app`. Every route lives in
`eesti/api/`, one module per thing the learner is doing.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import api, guest, identity, logs
from .evidence import NotRestored
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

# Issued items carry signed fields (`itemref`); the server grades those fields,
# never a replacement answer key supplied by the page.

app = FastAPI(title="Eesti-Keelt", docs_url="/api/docs")


logs.setup()


class IdentityMiddleware:
    """Resolve identity for the whole ASGI request, including sync route threads.

    Starlette's BaseHTTPMiddleware wrapper starts the downstream app in another
    task. ContextVar changes made around `call_next` do not reliably reach that
    task, so scope is set in this pure ASGI layer and copied by AnyIO when a sync
    endpoint runs in its worker thread.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, asgi_scope, receive, send):
        if asgi_scope["type"] != "http":
            await self.app(asgi_scope, receive, send)
            return

        request = Request(asgi_scope, receive)
        who = identity.resolve(request.headers, request.cookies, os.environ)
        started = time.monotonic()
        path = request.url.path
        method = request.method

        async def send_response(message):
            if message["type"] == "http.response.start":
                headers = [(key, value) for key, value in message.get("headers", [])
                           if key.lower() not in (b"x-boot-id", b"x-events-seq")]
                headers.append((b"x-boot-id", BOOT_ID.encode()))
                if path.startswith("/api/") and who is not None and who.permanent:
                    seq = _events_seq()
                    if seq is not None:
                        headers.append((b"x-events-seq", str(seq).encode()))
                if who is not None and who.is_guest and who.issued:
                    secure = "; Secure" if asgi_scope.get("scheme") == "https" else ""
                    cookie = (f"{identity.SANDBOX_COOKIE}={who.id}; HttpOnly{secure}; "
                              "SameSite=Lax; Max-Age=86400; Path=/")
                    headers.append((b"set-cookie", cookie.encode("latin-1")))
                message["headers"] = headers
                if path.startswith("/api/"):
                    logs.event("request", path=path, method=method,
                               status=message["status"],
                               ms=round((time.monotonic() - started) * 1000),
                               request_id=request.headers.get("cf-ray", ""), boot=BOOT_ID)
            await send(message)

        if who is None:
            response = JSONResponse({"detail": "not authorised"}, status_code=403)
            await response(asgi_scope, receive, send_response)
            return

        with identity.use(who):
            if who.is_guest:
                guest.ensure(who.id)
            await self.app(asgi_scope, receive, send_response)


app.add_middleware(IdentityMiddleware)


def _events_seq() -> int | None:
    """The log's last sequence number, read-only and without creating the file."""
    import sqlite3

    from . import config

    path = Path(config.learner_db("EVENTS_DB"))
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


@app.exception_handler(NotRestored)
async def _not_restored(request: Request, exc: NotRestored) -> JSONResponse:
    """Nothing was recorded: the instance is waiting for the Worker's restore."""
    return JSONResponse(
        {"detail": "Приложение восстанавливает прогресс. Повтори через несколько секунд."},
        status_code=503, headers={"retry-after": "5"})


api.register(app)
