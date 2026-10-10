"""Sõnastik: search the dictionary and open an entry (`eesti/dictionary.py`).

Both routes read reference tables and the learner's own word status; neither
asks a third party. The live dictionary is asked by the card's second request,
`/api/enrich/{word}`, as it always was, so an entry never waits on one.
"""

from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter, HTTPException

from .deps import db, review_db, vocab_db

router = APIRouter()


@router.get("/api/dictionary/search")
def dictionary_search(q: str = "", limit: int = 20) -> dict:
    """Entries for a query in any form (*majja* finds *maja*), a beginning, or a
    Russian word; Vabamorf's spelling suggestions when nothing matches."""
    from .. import dictionary

    with closing(db()) as words, closing(vocab_db()) as store:
        return dictionary.search(words, q, store=store, limit=limit)


@router.get("/api/dictionary/entry/{lemma}")
def dictionary_entry(lemma: str) -> dict:
    """One lemma's entry: level, part of speech, forms, EKI's recordings,
    meanings in Russian, English and Ukrainian, examples, and every source."""
    from .. import dictionary

    with closing(db()) as words, closing(vocab_db()) as store, closing(review_db()) as review:
        audio = dictionary._audio()
        try:
            found = dictionary.entry(words, lemma, store=store, review=review, audio=audio)
        finally:
            if audio is not None:
                audio.close()
    if found is None:
        raise HTTPException(status_code=404, detail=(
            f"«{lemma[:60]}» нет в словарях приложения. Проверь написание или найди слово "
            "в другой форме."))
    return found
