"""The HTTP surface, one module per thing the learner is doing.

`app.py` was 1 975 lines and held every route, every request model, the
database helpers, the static files and the state snapshot. Nothing was wrong
with it; it was simply the file every change had to be made in.

The split is by what the learner is doing, because that is what the sections
of the app are (`library.MODES`) and it is how a change arrives: "the review
queue shows the wrong count" is one file now.

Routers are included in the order the handlers were written in, because
registration order decides which route answers when two patterns could match
the same URL -- `/api/library` and `/api/library/{item_id}` are the pair that
matters here.
"""

from __future__ import annotations

from fastapi import FastAPI

from . import (
    assets,
    exam,
    grammar,
    health,
    library,
    notion,
    practice,
    review,
    speech,
    state,
    vocab,
)

#: In registration order. See the note above: this is behaviour, not taste.
ROUTERS = (
    assets.router,
    health.router,
    grammar.router,
    notion.router,
    practice.router,
    library.router,
    review.router,
    speech.router,
    exam.router,
    vocab.router,
    state.router,
)


def register(app: FastAPI) -> FastAPI:
    for router in ROUTERS:
        app.include_router(router)
    return app


def paths(app: FastAPI | None = None) -> list[str]:
    """Every path this API serves.

    Not `app.routes`. FastAPI keeps an included router as a single lazy
    `_IncludedRouter` entry, so walking `app.routes` and filtering on
    `hasattr(r, "path")` -- which three tests did, correctly, while every route
    was declared on `app` itself -- returns four paths and no error. A check
    that silently measures nothing is the failure this repository has a habit
    about; the inventory is derived from the routers instead, which is where
    the routes actually are.

    Pass an app to include anything registered on it directly (FastAPI's own
    `/api/docs`, `/openapi.json`).
    """
    found = {route.path for router in ROUTERS for route in router.routes}
    if app is not None:
        found |= {r.path for r in app.routes if hasattr(r, "path")}
    return sorted(found)
