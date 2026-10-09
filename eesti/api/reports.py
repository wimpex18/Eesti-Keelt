"""Checked material in the app: read it, answer it, report a mistake in it (ADR-0009).

`/api/material/units/{unit_id}` serves a unit's checked dialogues and texts
without their keys; `/api/material/answer` grades an answer by code against the
stored key and counts it; `/api/material/report` is *Teata veast*. Answers and
reports feed the statistics that retire items (`eesti/material/stats.py`), and
a retired item is no longer served.

Every scope may use them: the material is public, an answer is the learner's
own practice (recorded in their evidence log as `comprehension`), and the
shared counts keep no learner's words.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .deps import content_db

router = APIRouter()


def _shared() -> sqlite3.Connection:
    """The owner's snapshotted `progress.db`, which every scope counts in."""
    from .. import config

    return sqlite3.connect(config.PROGRESS_DB)


def _material(ident: str):
    from ..material import store

    with closing(content_db()) as conn:
        material = store.find(conn, ident)
    if material is None:
        raise HTTPException(status_code=404, detail="Этот материал не найден.")
    return material


def _gap_prompt(material, gap) -> str:
    from ..material.blind import _blank
    from ..material.gates import GAP_FORMS

    line = material.segments()[gap.at]
    return f"{_blank(line, gap.word)} ({gap.lemma}, {GAP_FORMS[gap.form]})"


def _served(material, gone: dict[str, str]) -> dict:
    from ..material import LABEL

    names = {s.id: s.name for s in material.speakers}
    return {
        "id": material.ident(),
        "kind": material.kind,
        "title": material.title,
        "harno": material.harno,
        "turns": [{"speaker": names[t.speaker], "text": t.text} for t in material.turns],
        "speakers": [{"name": s.name, "role_ru": s.role_ru} for s in material.speakers],
        "paragraphs": material.paragraphs,
        "off_list": [o.model_dump() for o in material.off_list],
        "questions": [{"id": q.id, "question": q.question}
                      for q in material.questions if q.id not in gone],
        "gaps": [{"id": g.id, "prompt": _gap_prompt(material, g)}
                 for g in material.gaps if g.id not in gone],
        "label": LABEL,
        "engine": material.authoring.engine,
        "prompt_version": material.authoring.prompt_version,
    }


@router.get("/api/material/units/{unit_id}")
def unit_material(unit_id: str) -> dict:
    """A unit's checked dialogues and texts, keys withheld, retired items left out."""
    from ..material import stats, store
    from ..units import by_id

    try:
        by_id(unit_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Такого раздела нет.") from None
    with closing(content_db()) as conn:
        found = store.for_unit(conn, unit_id)
    out = []
    with closing(_shared()) as shared:
        for material in found:
            gone = stats.retired(shared, material.ident())
            if stats.WHOLE in gone:
                continue
            out.append(_served(material, gone))
    return {"unit": unit_id, "material": out}


class MaterialAnswer(BaseModel):
    material: str = Field(max_length=120)
    item: str = Field(max_length=12)
    answer: str = Field(default="", max_length=400)


@router.post("/api/material/answer")
def material_answer(req: MaterialAnswer) -> dict:
    """Code grades the answer against the stored key; the answer is counted."""
    from .. import comprehension, evidence, identity
    from ..material import stats
    from ..material.gates import GAP_FORMS

    material = _material(req.material)
    question = next((q for q in material.questions if q.id == req.item), None)
    gap = next((g for g in material.gaps if g.id == req.item), None)
    if question is not None:
        verdict = comprehension.grade(
            comprehension.Question(0, question.question, question.answer,
                                   material.authoring.engine), req.answer)
        asked, expected = question.question, question.answer
    elif gap is not None:
        correct = comprehension.normalise(req.answer) == comprehension.normalise(gap.word)
        verdict = {"correct": correct, "expected": gap.word, "why_ru": (
            "Верно." if correct else
            f"Нужная форма: «{gap.word}» ({gap.lemma}, {GAP_FORMS[gap.form]}).")}
        asked, expected = _gap_prompt(material, gap), gap.word
    else:
        raise HTTPException(status_code=404, detail="Этот вопрос не найден.")
    scope = identity.current()
    with closing(_shared()) as shared:
        retired = stats.record_answer(shared, req.material, req.item,
                                      correct=verdict["correct"], answer=req.answer,
                                      permanent=scope.permanent)
    # Reading practice, replayable: the question and key travel with the attempt.
    evidence.record("comprehension", {
        "item": req.material, "idx": req.item, "correct": verdict["correct"],
        "question": asked, "expected": expected, "material": material.kind,
        "kind": "question" if question is not None else "gap",
        "engine": material.authoring.engine,
    })
    return {"item": req.item, **verdict, "retired": bool(retired)}


class MaterialReport(BaseModel):
    material: str = Field(max_length=120)
    #: A question or gap id; empty for the text as a whole.
    item: str = Field(default="", max_length=12)
    reason: str = Field(max_length=20)
    note: str = Field(default="", max_length=1000)


@router.post("/api/material/report")
def material_report(req: MaterialReport) -> dict:
    """*Teata veast*: keep the report; enough of them retire the item."""
    from .. import identity
    from ..material import stats

    material = _material(req.material)
    if req.reason not in stats.REASONS:
        raise HTTPException(status_code=422, detail="Неизвестная причина.")
    items = {q.id for q in material.questions} | {g.id for g in material.gaps}
    if req.item and req.item not in items:
        raise HTTPException(status_code=404, detail="Этот вопрос не найден.")
    with closing(_shared()) as shared:
        retired = stats.record_report(shared, req.material, req.item,
                                      reason=req.reason, note=req.note,
                                      scope=identity.current())
    return {"recorded": True, "retired": bool(retired)}
