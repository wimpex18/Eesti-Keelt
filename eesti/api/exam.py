"""Am I ready: official material, the verdict, and the mixed checkpoint.

The verdict reports four exam parts separately and never as one total, and it
says in Russian that it is not a prediction — a caveat nobody can read is not
a caveat.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..config import LEVELS
from .deps import content_db, content_available, db, notion_db, progress_db, vocab_db
from .render import _glosses_for, item_for_page

router = APIRouter()

@router.get("/api/exam/{level}")
def exam(level: str) -> dict:
    """The whole exam section for one level, in one request."""
    from ..library import exam_material

    if level not in LEVELS + ("B2", "C1"):
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    return exam_material(content_db(), level)


@router.get("/api/readiness/{level}")
def exam_readiness(level: str) -> dict:
    """Evidence for and against sitting a level. Not a prediction: every part is
    reported separately, since any part at zero fails.
    """
    from ..readiness import readiness

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")

    return readiness(
        level, progress=progress_db(), vocabulary=vocab_db(), words=db(),
        content=content_db(), notion=notion_db(),
    ).to_dict()


@router.get("/api/checkpoint/{level}")
def checkpoint_items(level: str, count: int = 15, seed: int | None = None) -> dict:
    """A mixed set across a whole level — interleaved by construction."""
    import secrets

    from ..checkpoint import PASS_MARK, build, ready, topics_at
    from ..itemref import checkpoint_ref, sign

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    seed = seed if seed is not None else secrets.randbelow(2**31)
    items = build(level, count=count, seed=seed)
    return {
        "level": level,
        "ready": ready(progress_db(), level),
        "pass_mark": PASS_MARK,
        "topics": topics_at(level),
        "items": [
            item_for_page(i) | {"token": sign(i, checkpoint_ref(
                level, seed=seed, count=count, index=n))}
            for n, i in enumerate(items)
        ],
        # Glosses for the checkpoint's words from the local store only, never a live
        # lookup per item.
        "glosses": _glosses_for([i.lemma for i in items]),
    }


class CheckpointResult(BaseModel):
    asked: int = Field(ge=1, le=30)
    correct: int = Field(ge=0)


@router.post("/api/checkpoint/{level}/result")
def checkpoint_result(level: str, res: CheckpointResult) -> dict:
    """Record a finished checkpoint taken on the page.

    Each answer was already graded and recorded by `/api/practice/answer`; this
    closes the set, so readiness can see that a level's checkpoint was passed. The
    tally comes from the page, as the items do (see the note in `eesti/app.py`).
    """
    from ..checkpoint import PASS_MARK, save

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    if res.correct > res.asked:
        raise HTTPException(status_code=400, detail="correct exceeds asked")
    passed = save(progress_db(), level, res.asked, res.correct)
    return {"level": level, "passed": passed, "pass_mark": PASS_MARK}


# --------------------------------------------------------------------------
# The exam itself: its shape, its sittings, and the one being prepared for
# --------------------------------------------------------------------------

@router.get("/api/exam-spec/{level}")
def exam_spec(level: str) -> dict:
    """What the exam is: parts, minutes, points and the pass rule (`eesti/exam.py`)."""
    from ..exam import NEXT_YEAR, SPECS, upcoming

    if level not in SPECS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    return SPECS[level].to_dict() | {
        "sessions": [s.to_dict() for s in upcoming(level)],
        "next_year": NEXT_YEAR,
    }


class GoalRequest(BaseModel):
    level: str
    #: The sitting, `YYYY-MM-DD`; null keeps the level with no date yet.
    sitting: str | None = None


@router.get("/api/goal")
def read_goal() -> dict:
    """The sitting being prepared for, or null."""
    from ..exam import goal

    chosen = goal(progress_db())
    return {"goal": chosen.to_dict() if chosen else None}


@router.post("/api/goal")
def choose_goal(req: GoalRequest) -> dict:
    """Choose the sitting to prepare for. The countdown follows it."""
    from datetime import date

    from ..exam import set_goal

    try:
        when = date.fromisoformat(req.sitting) if req.sitting else None
    except ValueError as exc:
        raise HTTPException(status_code=400,
                            detail="Дата экзамена — в виде ГГГГ-ММ-ДД.") from exc
    try:
        chosen = set_goal(progress_db(), req.level, when)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"goal": chosen.to_dict()}


@router.get("/api/goal.ics")
def goal_calendar() -> PlainTextResponse:
    """The sitting and its registration deadline, for a calendar app."""
    from ..exam import calendar, goal

    chosen = goal(progress_db())
    if chosen is None or not (chosen.sitting or chosen.registration_closes):
        raise HTTPException(status_code=404, detail="Сессия ещё не выбрана.")
    return PlainTextResponse(
        calendar(chosen), media_type="text/calendar",
        headers={"content-disposition": 'attachment; filename="eesti-keelt-eksam.ics"'})


# --------------------------------------------------------------------------
# The timed mock: one exam part, on the exam's clock
# --------------------------------------------------------------------------

@router.get("/api/mock/{level}/{part}")
def mock_section(level: str, part: str, seed: int | None = None) -> dict:
    """A section to sit: its minutes, its tasks, and what it is (`eesti/mock.py`)."""
    import secrets

    from ..exam import SPECS
    from ..itemref import mock_ref, sign
    from ..mock import build

    if level not in SPECS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    seed = seed if seed is not None else secrets.randbelow(2**31)
    try:
        section = build(level, part, seed=seed,
                        content=content_db() if content_available() else None,
                        words=db(), vocabulary=vocab_db())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    body = section.to_dict() | {"seed": seed}
    if section.kind == "cloze":
        # Graded from the token, as any drill is; the page sends it back.
        body["tasks"] = [
            item_for_page(task) | {"token": sign(task, mock_ref(level, part, seed=seed,
                                                                index=n))}
            for n, task in enumerate(section.tasks)
        ]
        body["glosses"] = _glosses_for([t.lemma for t in section.tasks])
    if not body["tasks"]:
        body["detail"] = ("Для этой части нужен корпус текстов, а он ещё не "
                          "загружен на сервер.")
    return body


class MockAnswer(BaseModel):
    token: str = ""
    given: str = ""
    #: Dictation: what was heard, against the sentence the page was given.
    text: str = ""


class MockResult(BaseModel):
    seconds: float = Field(ge=0)
    answers: list[MockAnswer] = Field(default_factory=list)
    #: Writing: the text produced. Speaking: nothing — the exam is paired.
    written: str = ""


@router.post("/api/mock/{level}/{part}")
def mock_result(level: str, part: str, res: MockResult) -> dict:
    """Grade a finished section and record it as exam evidence."""
    from ..exam import SPECS
    from ..itemref import verify
    from ..mock import record

    if level not in SPECS or part not in {p.id for p in SPECS[level].parts}:
        raise HTTPException(status_code=404, detail="unknown level or part")

    asked, correct, detail = len(res.answers), None, {}
    if part == "lugemine":
        correct = 0
        for answer in res.answers:
            try:
                issued = verify(answer.token)["item"]
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=(
                    "Задание не удалось проверить: оно выдано не этим сервером.")) from exc
            correct += int(answer.given.strip().casefold()
                           == issued["answer"].strip().casefold())
    elif part == "kuulamine":
        from ..dictation import Passage, grade, key_of

        correct = 0
        for answer in res.answers:
            if not answer.text:
                continue
            got = grade(Passage(answer.text, key_of(answer.text),
                                len(answer.text.split())), answer.given)
            correct += int(got.correct)
    elif part == "kirjutamine":
        from ..mock import check_writing

        detail = check_writing(res.written, level)
        # Long enough and clean by the deterministic checks. What a model would
        # say about it belongs in Kirjutamine, labelled, never in a mock's score.
        asked, correct = 1, int(detail["long_enough"] and detail["errors"] == 0)
    else:                                   # raakimine: practised, never scored
        asked, correct = len(res.answers) or 1, None

    saved = record(progress_db(), level, part, res.seconds, asked, correct,
                   detail=detail)
    return saved | {"minutes": SPECS[level].part(part).minutes}


@router.get("/api/mock-run/{level}")
def mock_run(level: str) -> dict:
    """A whole sitting: the four parts in the order the exam runs them, with the
    total time it takes. Each part is still sat and recorded on its own."""
    from ..exam import SPECS

    if level not in SPECS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    spec = SPECS[level]
    return {
        "level": level,
        "parts": [p.id for p in spec.parts],
        "minutes": sum(p.minutes for p in spec.parts),
        "total": spec.total,
        "pass_mark": spec.pass_mark,
        "note": ("Четыре части подряд, каждая на своём времени — как на "
                 "экзамене. Между частями можно остановиться: каждая "
                 "записывается отдельно. Говорение (rääkimine) не оценивается."),
    }


@router.get("/api/mock/{level}")
def mock_history(level: str) -> dict:
    """Sections sat at this level, newest first, and how many of each part."""
    from ..mock import counts, history

    return {"level": level, "sections": history(progress_db(), level),
            "counts": counts(progress_db(), level)}


@router.get("/api/exam/file/{item_id}")
def exam_file(item_id: str):
    """One downloaded exam file: the task PDF, or its listening recording.

    Only files under `config.EXAM_DIR` are served, and only to the learner —
    Access guards the app, and this is the exam board's material.
    """
    import json as _json
    from pathlib import Path

    from fastapi.responses import FileResponse

    from .. import config

    row = content_db().execute(
        "SELECT title, meta FROM items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Материал не найден.")
    try:
        meta = _json.loads(row["meta"] or "{}")
    except ValueError:
        meta = {}
    stored = meta.get("file")
    if not stored:
        raise HTTPException(status_code=404, detail=(
            "Этот материал не скачан — открой его по ссылке."))
    root = Path(config.EXAM_DIR).resolve()
    path = (root / stored).resolve()
    if root not in path.parents or not path.exists():
        # A meta row pointing outside the folder is a bug, not a request to obey.
        raise HTTPException(status_code=404, detail="Файл недоступен.")
    kinds = {".pdf": "application/pdf", ".mp3": "audio/mpeg",
             ".wav": "audio/wav", ".docx":
             "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    return FileResponse(path, media_type=kinds.get(path.suffix.lower(),
                                                   "application/octet-stream"),
                        filename=path.name)


@router.get("/api/exam/text/{item_id}")
def exam_text(item_id: str) -> dict:
    """The task's own text, extracted from the PDF, for reading it in the app."""
    import json as _json

    row = content_db().execute(
        "SELECT title, skill, level, body, audio_url, meta FROM items WHERE id = ?",
        (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Материал не найден.")
    if not (row["body"] or "").strip():
        raise HTTPException(status_code=404, detail=(
            "Текст этого задания не разобрался — открой файл."))
    try:
        meta = _json.loads(row["meta"] or "{}")
    except ValueError:
        meta = {}
    return {"id": item_id, "title": row["title"], "skill": row["skill"],
            "level": row["level"], "text": row["body"],
            # An EIS listening task is several short recordings, one per
            # question; a HARNO task has its own file instead.
            "audio": meta.get("audio") or ([row["audio_url"]] if row["audio_url"] else []),
            "url": meta.get("url"),
            "note": "Официальное задание — © Haridus- ja Noorteamet."}
