"""Local single-user web app. No auth, no deployment, no cloud state.

Run with:  python -m eesti.cli serve

This module is the assembly: the application object, the one piece of
middleware that guards the origin, and the names that the CLI, the tests and
the deployment scripts import from `eesti.app`. Every route lives in
`eesti/api/`, one module per thing the learner is doing.
"""

from __future__ import annotations

import hmac
import os

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
# The four learner database paths are deliberately NOT re-exported here.
#
# They were, and `docs/lessons.md` has the entry: two names for one file is a
# fork waiting to happen. It happened twice. `app.py` first kept its own copies
# bound at import, so `_state_paths()` read one set and the database helpers
# the other and a restore could land in a file the app never opened. That was
# fixed by importing them from `config` -- which left a second *name* for each
# path, and ten test fixtures patching both, and one loop that deletes files
# reading whichever name it happened to be given.
#
# Everything reads `eesti.config` now, at call time, including the tests.

# Generated items are not stored, so an answer arrives without the question. The
# client sends the item back with the answer and the server re-grades it, which
# keeps the API stateless -- but it also means the client could send an item it
# was never given. That is fine for a single-user app behind Cloudflare Access
# and would not be for a multi-user one: the fix there is to sign the item or
# hold the session server-side, and this note exists so that is a decision
# rather than an oversight.

app = FastAPI(title="Eesti-Keelt", docs_url="/api/docs")


@app.middleware("http")
async def _proxy_guard(request: Request, call_next):
    """Keep the origin from becoming a way around the front door.

    On Cloud Run the service is invoked unauthenticated -- that is what makes it
    free -- so its `run.app` URL answers the whole internet. Cloudflare Access
    sits in front of the *Worker*, not in front of that URL, so without this the
    Access policy would guard one of two doors and the harvested material it
    exists to protect would be a hostname guess away.

    `PROXY_TOKEN` is a secret only the Worker holds. Unset, the guard is off,
    because the default way to run this app is `cli serve` on a laptop and
    demanding a token there would be ceremony. `/api/health` reports which of
    the two it is, so "is the deployment actually closed?" has an answer you can
    check rather than assume.
    """
    expected = os.environ.get("PROXY_TOKEN")
    if expected and not hmac.compare_digest(
        request.headers.get(PROXY_HEADER, ""), expected
    ):
        return JSONResponse({"detail": "not authorised"}, status_code=403)
    response = await call_next(request)
    response.headers["x-boot-id"] = BOOT_ID
    return response


api.register(app)
