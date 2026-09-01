"""The vocabulary ladder: browsing it, and moving a word up it.

`POST /api/vocab/known` is the only way a word can become known from the
deployment — its other caller is the CLI, which does not run there. That made
it the worst orphan this project has had, and is why every route now has to
have a caller (`tests/test_route_inventory.py`).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .deps import db, vocab_db

router = APIRouter()

class KnownWords(BaseModel):
    lemmas: list[str] = Field(min_length=1, max_length=200)
    long_known: bool = False
    #: `known` (default), `long_known`, or `ignore`. The ladder has five values
    #: and until now only two had any writer: `õpin`, set automatically on the
    #: first encounter while reading, and `tean`, set by the button. `eiran`,
    #: `teadsin ammu` and `tuttav` were modelled, stored, counted — and
    #: unreachable, which is this project's most recurring bug wearing another
    #: hat.
    status: str | None = None


@router.get("/api/vocab")
def vocab_browse(
    level: str | None = None,
    pos: str | None = None,
    status: str | None = None,
    limit: int = 60,
    offset: int = 0,
) -> dict:
    """Browse the wordlist. The app could look a word up and could not list any.

    A learner cannot ask for a word they have not met, which is precisely the
    set worth studying, so lookup-only made 160 316 words reachable only by
    somebody who already knew what was in there. Filters are level, part of
    speech and what the learner has already marked.

    Needs the built wordlist, and asks whether one exists rather than opening
    the path and trusting it: `wordlist.connect` creates the file and applies
    the schema, so an unbuilt path hands back a complete-looking database with
    no words in it, which reads as "the vocabulary is empty" rather than
    "nothing has been built here". This used to borrow `cli.words_db` for that
    -- the web app reaching into the command line tool for a database opener,
    and printing its instruction to the server log where nobody reads it.
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

    Marking a word known is an explicit act — never inferred from reading. A
    word skimmed past is not a word learned, and a counter that inflates itself
    measures reading rather than vocabulary.

    `ignore` is the one a vocabulary list needs and a reader does not. Browsing
    B1 nouns turns up `riigivisiit` and `seinamaaling`: real words, correctly
    listed, and not what this learner is going to spend a morning on. Without a
    way to say so they come back on every page and the "still to learn" count
    never means anything. All three are *settled* — the app stops proposing
    them — and they stay distinguishable, because "I know this" and "this is
    not for me" are different facts about a learner.
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
