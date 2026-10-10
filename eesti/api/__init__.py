"""The HTTP surface, one module per thing the learner is doing.

Routers are included in a fixed order, because registration order decides which
route answers when two patterns match (`/api/library` and
`/api/library/{item_id}`).
"""

from __future__ import annotations

from fastapi import FastAPI

from . import (
    assets,
    dictionary,
    exam,
    grammar,
    health,
    library,
    notion,
    practice,
    profile,
    reports,
    review,
    sources,
    speech,
    state,
    vocab,
)

#: In registration order. See the note above: this is behaviour, not taste.
ROUTERS = (
    assets.router,
    health.router,
    grammar.router,
    dictionary.router,
    notion.router,
    practice.router,
    library.router,
    reports.router,
    review.router,
    sources.router,
    speech.router,
    exam.router,
    vocab.router,
    profile.router,
    state.router,
)


def register(app: FastAPI) -> FastAPI:
    for router in ROUTERS:
        app.include_router(router)
    return app


def paths(app: FastAPI | None = None) -> list[str]:
    """Every path this API serves, derived from the routers.

    Not `app.routes`: FastAPI keeps an included router as one lazy entry, so that
    walk silently returns almost nothing. Pass an app to include routes registered
    on it directly (`/api/docs`, `/openapi.json`).
    """
    found = {route.path for router in ROUTERS for route in router.routes}
    if app is not None:
        found |= {r.path for r in app.routes if hasattr(r, "path")}
    return sorted(found)
