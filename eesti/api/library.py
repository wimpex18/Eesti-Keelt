"""The material: what is in it, what to read next, and opening one item.

Sections filter on skill *and* purpose (`meta.kind`); `/api/modes` is the map.
`/api/reading/next` ranks by the share of words within this learner's reach, never by a
CEFR level derived from vocabulary.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..lookup import annotate
from ..sources import count as content_count
from ..sources import query as content_query
from .deps import content_db, db, progress_db, vocab_db

router = APIRouter()

@router.get("/api/modes")
def modes() -> dict:
    """The three modes and what is in each, in one request."""
    from ..library import MODE_LABELS, MODES, sections as library_sections

    conn = content_db()
    return {
        "modes": [
            {
                "id": mode,
                "et": MODE_LABELS[mode][0],
                "ru": MODE_LABELS[mode][1],
                "sections": library_sections(conn, mode=mode),
            }
            for mode in MODES
        ]
    }


@router.get("/api/library")
def library(skill: str = "lugemine", section: str | None = None,
            level: str | None = None, band: str | None = None,
            limit: int = 60, offset: int = 0) -> dict:
    """Harvested study material, by skill or by section.

    Prefer `section`: it also applies the `kind` filters a skill alone ignores.
    `public_only` is not a parameter — a caller must not be able to request
    owner-only material by guessing.
    """
    conn = content_db()
    if section is not None:
        from ..library import browse
        from ..library import count as section_count

        try:
            rows = browse(conn, section=section, level=level, band=band,
                          limit=limit)
            total = section_count(conn, section=section, level=level, band=band)
        except KeyError as exc:
            raise HTTPException(
                status_code=404, detail=f"unknown section {section!r}") from exc
    else:
        rows = content_query(conn, skill=skill, level=level, band=band,
                             limit=limit, offset=offset)
        total = content_count(conn, skill=skill, level=level, band=band)
    return {
        # The section total, not the page length.
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r["id"],
                "title": r["title"],
                "level": r["level"],
                "band": r["band"],
                "source": r["source_name"],
                "licence": r["licence"],
                "audio_url": r["audio_url"],
                "words": len(( r["body"] or "").split()),
                # Official exam tasks are pointers (HARNO copyright, scored on their page); the UI
                # links out instead of opening an empty reader.
                **_pointer(r["meta"]),
            }
            for r in rows
        ]
    }


def _pointer(meta: str | None) -> dict:
    """`{"external": True, "url": ...}` for an indexed task, else `{}`."""
    try:
        data = json.loads(meta or "{}")
    except ValueError:
        return {}
    if not data.get("external"):
        return {}
    return {"external": True, "url": data.get("url"), "note": data.get("note")}


@router.get("/api/reading/next")
def reading_next(limit: int = 6, section: str = "lugemine") -> dict:
    """Texts to read next, ranked by how much of each is within this learner's reach.

    `coverage` is the share of running words the learner knows or the word list puts
    at A1–A2 (`difficulty.within_reach`). Texts below `difficulty.FLOOR` are not
    recommended; when none clears it, the most reachable come back with `fallback`
    set rather than an empty list. Inside one coverage step, shorter goes first.
    """
    from ..difficulty import (FLOOR, INSTRUCTIONAL, REACH_LEVELS, known_lemmas,
                              reach_lemmas, recommend, within_reach)
    from ..library import browse
    from ..library import count as section_count

    known = known_lemmas(vocab_db())
    reach = reach_lemmas(db())
    # Score the whole shelf, so any text can be recommended.
    conn = content_db()
    rows = browse(conn, section, limit=max(1, section_count(conn, section)))

    scored = []
    unmeasurable = 0
    for row in rows:
        if not (row["body"] or "").strip():
            continue
        if not (known or reach):
            # No word list and nothing marked known: every text would score 0 %,
            # which is "not measured", not "too hard".
            unmeasurable += 1
            continue
        profile = within_reach(row["body"], known, reach)
        if profile["total"] == 0:
            unmeasurable += 1
            continue
        scored.append({
            "id": row["id"], "title": row["title"], "band": row["band"],
            "source": row["source_name"], "audio_url": row["audio_url"],
            **profile,
        })

    picked = recommend(scored, limit)
    levels = "–".join((REACH_LEVELS[0], REACH_LEVELS[-1]))
    note = (
        f"Сначала тексты, где больше всего посильных слов — знакомых вам или "
        f"уровней {levels} по словарному списку; из похожих — сначала короче. "
        f"Тексты, где посильных слов меньше {round(FLOOR * 100)} %, не "
        f"предлагаются. Это доля слов, а не уровень текста и не оценка понимания."
    )
    if picked["fallback"]:
        note = (
            f"Ни в одном тексте посильных слов (знакомых или уровней {levels}) "
            f"не набирается {round(FLOOR * 100)} % — показаны самые доступные. "
            f"Читайте их со словарём: нажмите на слово."
        )
    if not scored and unmeasurable:
        note = (
            "Словарный список не собран, поэтому долю посильных слов посчитать "
            "нельзя — это не значит, что тексты трудные. Соберите его командами "
            "`cli fetch-data` и `cli build`; в образе он собирается при сборке."
        )
    return {
        "items": picked["items"],
        "known_words": len(known),
        "threshold": INSTRUCTIONAL,
        # Nothing cleared `FLOOR`: the items are the least hard, not a fit.
        "fallback": picked["fallback"],
        # Distinguishes "the library is empty" from "nothing could be measured".
        "unmeasurable": unmeasurable,
        "note": note,
    }


@router.get("/api/library/{item_id}")
def library_item(item_id: str, minutes: float = 0.0) -> dict:
    """One item with its full text and vocabulary profile; opening records exposure
    and word encounters via `library.open_item`.

    Encounters are not knowledge: they bump a met-count and never mark a word known.
    """
    conn = content_db()
    row = conn.execute(
        """SELECT i.*, s.name AS source_name, s.licence
           FROM items i JOIN sources s ON s.id = i.source_id
           WHERE i.id = ?""",
        (item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Этот материал не найден — возможно, он ещё не загружен на сервер.")

    from ..library import open_item

    # Never let bookkeeping cost the learner the text they asked for.
    try:
        opened = open_item(conn, item_id, progress=progress_db(),
                           vocabulary=vocab_db(), minutes=minutes)
    except Exception:  # noqa: BLE001 - reading must work with no databases
        opened = {"lemmas": 0}

    return {
        "id": row["id"],
        "title": row["title"],
        "met_lemmas": opened.get("lemmas", 0),
        "body": row["body"],
        "level": row["level"],
        "source": row["source_name"],
        "licence": row["licence"],
        "audio_url": row["audio_url"],
        "band": row["band"],
        # The reader needs to know *what kind of thing* this is before it can
        # decide between a text, a player and an embed.
        "meta": json.loads(row["meta"] or "{}"),
        "url": json.loads(row["meta"] or "{}").get("url"),
        "profile": annotate(row["body"] or ""),
    }


# --------------------------------------------------------------------------
# Reading comprehension: a model writes the questions, the text keys them
# --------------------------------------------------------------------------
#
# ADR-0004. The answer travels no further than the server: the page is sent the
# questions only, and `/api/read/answer` compares what the learner wrote with
# the span stored beside the text.

class ReadAnswer(BaseModel):
    item_id: str
    idx: int
    answer: str = Field(default="", max_length=400)


def _text_of(item_id: str) -> str:
    row = content_db().execute(
        "SELECT body FROM items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Этот материал не найден.")
    return row["body"] or ""


def _long_enough(text: str) -> bool:
    """Counted the way `comprehension.make` counts, so the button is offered
    exactly when asking would work: `split()` also counts numerals and dashes,
    and a timetable would be offered questions it can never get."""
    from .. import comprehension

    return comprehension.long_enough(text)


@router.get("/api/read/questions/{item_id}")
def read_questions(item_id: str) -> dict:
    """The questions already written for this text. Never generates: a page that
    opens a text must not wait on a model."""
    from .. import comprehension, evidence

    text = _text_of(item_id)
    with evidence.connect() as log:
        made = comprehension.stored(log, item_id)
    return {
        "item_id": item_id,
        "questions": [q.asked() for q in made],
        # Whether asking for questions is worth the learner's tap.
        "can_make": _long_enough(text),
    }


@router.post("/api/read/questions/{item_id}")
def make_questions(item_id: str) -> dict:
    """Write the questions for this text, once, and keep them.

    An empty list is an honest answer: nothing the model proposed had its answer
    in the text.
    """
    from .. import comprehension, evidence

    text = _text_of(item_id)
    with evidence.connect() as log:
        made = comprehension.make(log, item_id, text)
    return {
        "item_id": item_id,
        "questions": [q.asked() for q in made],
        "can_make": _long_enough(text),
        # The page stops offering the button after a round that produced
        # nothing, so a text the model cannot key does not cost a call a tap.
        "tried": True,
        "note": ("" if made else
                 "Вопросы не получились: ни один ответ не нашёлся в тексте "
                 "дословно. Попробуй другой текст."),
    }


@router.post("/api/read/answer")
def read_answer(req: ReadAnswer) -> dict:
    """Grade one answer against the text's own words, and record the practice."""
    from .. import comprehension, evidence

    with evidence.connect() as log:
        questions = {q.idx: q for q in comprehension.stored(log, req.item_id)}
    question = questions.get(req.idx)
    if question is None:
        raise HTTPException(status_code=404, detail="Этот вопрос не найден.")
    verdict = comprehension.grade(question, req.answer)
    # Reading practice, and the only event that counts for the `lugemine` part.
    # The question travels with it: an attempt must be replayable even after the
    # text is asked about again with a new set.
    evidence.record("comprehension", {
        "item": req.item_id, "idx": req.idx, "correct": verdict["correct"],
        "question": question.question, "expected": question.answer,
        "engine": question.engine, "v": comprehension.VERSION,
    })
    return {"idx": req.idx, **verdict}
