"""The vocabulary ladder: browsing it, and moving a word up it.

`POST /api/vocab/known` is the only way a word becomes known on the deployment;
every route must have a caller.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .deps import db, vocab_db

router = APIRouter()

class KnownWords(BaseModel):
    lemmas: list[str] = Field(min_length=1, max_length=200)
    long_known: bool = False
    #: `known` (default), `long_known`, or `ignore` — the three settled statuses the
    #: learner sets. `õpin` is set by meeting a word while reading.
    status: str | None = None


@router.get("/api/vocab")
def vocab_browse(
    level: str | None = None,
    pos: str | None = None,
    status: str | None = None,
    limit: int = 60,
    offset: int = 0,
) -> dict:
    """Browse the word list by level, part of speech and the learner's status.

    Checks `wordlist.available` first, so an unbuilt path reports "nothing built"
    rather than an empty vocabulary.
    """
    from .. import vocab as vocab_mod
    from ..wordlist import available

    words = db() if available() else None
    if words is None:
        raise HTTPException(
            503,
            "Словарь ещё не собран на этом сервере — запусти "
            "`python -m eesti.cli fetch-data`, затем `python -m eesti.cli build`.",
        )
    try:
        return vocab_mod.browse(
            words, vocab_db(), level=level, pos=pos, status=status,
            limit=max(1, min(limit, 200)), offset=max(0, offset),
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/vocab/known")
def vocab_known(req: KnownWords) -> dict:
    """Settle a word: known, long known, or not worth studying.

    Always an explicit act, never inferred from reading. `ignore` removes words the
    learner will not study from lists and counts; all three are distinct facts.
    """
    from ..vocab import IGNORED, KNOWN, WELL_KNOWN, set_status

    choice = (req.status or "").strip().lower()
    if choice and choice not in ("known", "long_known", "ignore"):
        raise HTTPException(
            422, f"status must be known, long_known or ignore, not {choice!r}")
    if choice == "ignore":
        status_ = IGNORED
    elif choice == "long_known" or req.long_known:
        status_ = WELL_KNOWN
    else:
        status_ = KNOWN

    vocabulary = vocab_db()
    for lemma in req.lemmas:
        set_status(vocabulary, lemma.strip().lower(), status_)
    return {"marked": len(req.lemmas), "status": status_}
