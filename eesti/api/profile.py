"""The profile and the guest sandbox (ADR-0006)."""

from __future__ import annotations

from contextlib import ExitStack, closing

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class NameRequest(BaseModel):
    #: Null or blank clears the name.
    name: str | None = None


@router.get("/api/me")
def me() -> dict:
    """`profile.summary` for the request's scope (`identity.current()`).

    """
    from .. import evidence, profile
    from ..identity import current
    from . import deps

    with ExitStack() as stack:
        log = stack.enter_context(closing(evidence.connect()))
        progress = stack.enter_context(closing(deps.progress_db()))
        reviews = stack.enter_context(closing(deps.review_db()))
        vocabulary = stack.enter_context(closing(deps.vocab_db()))
        return profile.summary(log=log, progress=progress, reviews=reviews,
                               vocabulary=vocabulary, scope=current())


@router.post("/api/me")
def rename(req: NameRequest) -> dict:
    """Set the name, then answer as `GET /api/me`.

    Allowed for guests too: it writes to their sandbox.
    """
    from .. import profile

    try:
        profile.set_name(req.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return me()


@router.post("/api/me/reset")
def reset_profile_progress() -> dict:
    """Reset study data for the current permanent account, preserving identity."""
    from .. import profile
    from ..identity import current

    if current().is_guest:
        raise HTTPException(status_code=403,
                            detail="Сброс прогресса доступен только постоянному аккаунту.")
    return profile.reset_progress()


@router.post("/api/me/restore")
def restore_profile_progress() -> dict:
    """Restore the latest reset point for the current permanent account."""
    from .. import profile
    from ..identity import current

    if current().is_guest:
        raise HTTPException(status_code=403,
                            detail="Восстановление прогресса доступно только постоянному аккаунту.")
    try:
        return profile.restore_progress()
    except profile.NoRestorableProgress as exc:
        raise HTTPException(status_code=409,
                            detail="Нет сброса прогресса, который можно восстановить.") from exc


@router.post("/api/guest/reset")
def guest_reset() -> dict:
    """Throw this guest sandbox away; the next request starts empty.

    """
    from .. import guest
    from ..identity import current

    scope = current()
    if not scope.is_guest:
        raise HTTPException(status_code=403,
                            detail="Очищать гостевую песочницу может только гость.")
    guest.reset(scope.id)
    return {"reset": scope.id}
