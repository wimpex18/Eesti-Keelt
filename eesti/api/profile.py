"""The profile and the guest sandbox (ADR-0006).

SKELETON, not yet in `eesti.api.ROUTERS`. Register it (before `state.router`)
once the routes work, and document it in `docs/architecture.md`.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class NameRequest(BaseModel):
    #: Null or blank clears the name.
    name: str | None = None


@router.get("/api/me")
def me() -> dict:
    """`profile.summary` for the request's scope (`identity.current()`).

    TODO(Luna): open the log and projections through `deps` (which resolve
    `config.learner_db`), call `profile.summary`, close them.
    """
    raise NotImplementedError


@router.post("/api/me")
def rename(req: NameRequest) -> dict:
    """Set the name, then answer as `GET /api/me`.

    TODO(Luna): `profile.set_name`; a ValueError is a 400 with its Russian text.
    Allowed for guests too: it writes to their sandbox.
    """
    raise NotImplementedError


@router.post("/api/guest/reset")
def guest_reset() -> dict:
    """Throw this guest sandbox away; the next request starts empty.

    TODO(Luna): 403 for a permanent scope, owner or learner (Russian detail);
    for a guest, `guest.reset(scope.id)` and answer `{"reset": scope.id}`.
    """
    raise NotImplementedError
