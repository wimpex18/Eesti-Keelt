"""Am I ready: official material, the verdict, and the mixed checkpoint.

The verdict reports four exam parts separately and never as one total, and it
says in Russian that it is not a prediction — a caveat nobody can read is not
a caveat.
"""

from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from ..config import LEVELS
from .deps import content_db, content_available, db, notion_db, progress_db, vocab_db
from .render import _glosses_for, item_for_page

router = APIRouter()
_PDF_LOCK = threading.Lock()  # PDFium calls are not thread-safe.

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


@router.get("/api/milestones/{level}")
def exam_milestones(level: str) -> dict:
    """Recognise actual practice without awarding points for attendance."""
    from ..milestones import for_level

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail="unknown level")
    return {"level": level, "milestones": for_level(progress_db(), level)}


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
    from ..examday import for_level

    return SPECS[level].to_dict() | {
        "sessions": [s.to_dict() for s in upcoming(level)],
        "next_year": NEXT_YEAR,
        # Eksamipäev: the day's rules from HARNO's information sheet.
        "exam_day": for_level(level),
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
def mock_section(level: str, part: str, seed: int | None = None, format: str = "",
                 task: int | None = None) -> dict:
    """A section to sit: its minutes, its tasks, and what it is (`eesti/mock.py`).
    `format=harno` gives reading or listening in HARNO's task types, and `task`
    one of them alone (`_harno_section`)."""
    import secrets

    if format == "harno":
        return _harno_section(level, part, task, seed)
    from ..exam import SPECS
    from ..itemref import mock_ref, sign
    from ..mock import build

    if level not in SPECS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    if ":" in part:
        # HARNO's task types are issued with `format=harno`, signed, never by name.
        raise HTTPException(status_code=404, detail=f"no such exam part: {part!r}")
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


class WrittenTask(BaseModel):
    #: The prompt answered (`eesti/writingtasks.py`), and what was written: a text,
    #: or a questionnaire's answers.
    id: str
    text: str = ""
    answers: list[str] = Field(default_factory=list, max_length=20)


class MockResult(BaseModel):
    seconds: float = Field(ge=0)
    answers: list[MockAnswer] = Field(default_factory=list, max_length=60)
    #: Writing: both tasks. `written` is a single text from a page cached
    #: before both tasks were set. Speaking: nothing — the exam is paired.
    tasks: list[WrittenTask] = Field(default_factory=list, max_length=2)
    written: str = ""
    #: `harno`: a part in HARNO's task types; `task` the one practised alone.
    format: str = ""
    task: int | None = None


@router.post("/api/mock/{level}/{part}")
def mock_result(level: str, part: str, res: MockResult) -> dict:
    """Grade a finished section and record it as exam evidence."""
    from ..exam import SPECS
    from ..item import accepts
    from ..itemref import verify
    from ..mock import record

    if level not in SPECS or part not in {p.id for p in SPECS[level].parts}:
        raise HTTPException(status_code=404, detail="unknown level or part")
    if res.format == "harno":
        return _harno_result(level, part, res)

    asked, correct, detail = len(res.answers), None, {}
    # Item by item, for the learner to look back at; not stored with the section.
    items: list[dict] = []
    if part == "lugemine":
        from ..item import fill

        correct = 0
        for answer in res.answers:
            try:
                issued = verify(answer.token)["item"]
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=(
                    "Задание не удалось проверить: оно выдано не этим сервером.")) from exc
            ok = accepts(issued["answer"], answer.given)
            correct += int(ok)
            items.append({"given": answer.given, "answer": issued["answer"],
                          "solution": fill(issued["prompt"], issued["answer"]),
                          "correct": ok, "topic": issued["topic"]})
    elif part == "kuulamine":
        from ..dictation import Passage, grade, key_of

        correct = 0
        for answer in res.answers:
            if not answer.text:
                continue
            got = grade(Passage(answer.text, key_of(answer.text),
                                len(answer.text.split())), answer.given)
            correct += int(got.correct)
            items.append({"text": answer.text, "given": answer.given,
                          "correct": got.correct, "missed": got.missed})
    elif part == "kirjutamine" and res.tasks:
        from .. import writingtasks

        checked = []
        for written in res.tasks:
            try:
                task = writingtasks.by_id(written.id)
            except KeyError as exc:
                raise HTTPException(status_code=400, detail="unknown writing task") from exc
            if task.level != level:
                raise HTTPException(status_code=400, detail="task from another level")
            checked.append(writingtasks.check(task, written.text, written.answers))
        detail = {"tasks": checked, "prompts_by": writingtasks.PROMPTS_BY}
        # A task counts when its checklist is complete; a model's reading of the
        # text, where there is one, is labelled advisory and never counts.
        asked, correct = len(checked), sum(writingtasks.met(r) for r in checked)
    elif part == "kirjutamine":
        from ..mock import check_writing

        detail = check_writing(res.written, level)
        asked, correct = 1, int(detail["long_enough"] and detail["errors"] == 0)
    else:                                   # raakimine: practised, never scored
        asked, correct = len(res.answers) or 1, None

    saved = record(progress_db(), level, part, res.seconds, asked, correct,
                   detail=detail)
    # The topics behind the misses, to practise next (ADR-0009: review → practice).
    practise = list(dict.fromkeys(i["topic"] for i in items
                                  if not i.get("correct") and i.get("topic")))
    return saved | {"minutes": SPECS[level].part(part).minutes, "items": items,
                    "practise": practise}


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
    """Sections sat at this level, newest first, how many of each part, and the
    HARNO task types due for a re-test (`mock.retests`)."""
    from datetime import date

    from ..mock import counts, history, retests

    return {"level": level, "sections": history(progress_db(), level),
            "counts": counts(progress_db(), level),
            "retests": retests(progress_db(), level), "today": date.today().isoformat()}


# --------------------------------------------------------------------------
# HARNO's task types (`/api/mock/...?format=harno`): a part in HARNO's format,
# its review, and its re-tests
# --------------------------------------------------------------------------

def _harno_part(level: str, part: str, task: int | None) -> str:
    """The section `mock.build` makes for this request: `lugemine:harno` or `lugemine:3`."""
    from ..exam import SPECS
    from ..harnotasks import by_number

    if level not in SPECS or part not in ("lugemine", "kuulamine"):
        raise HTTPException(status_code=404, detail="unknown level or part")
    if task is not None:
        try:
            by_number(level, part, task)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown task") from exc
    return f"{part}:{task if task is not None else 'harno'}"


def _harno_section(level: str, part: str, task: int | None, seed: int | None) -> dict:
    """A reading or listening part in HARNO's task types (`eesti/harnotasks.py`),
    or one type alone (`task`, HARNO's number) to practise it. Each question
    comes with a signed token and without its key; an empty `tasks` means no
    type could be built here and the page uses `/api/mock` instead."""
    import secrets

    from ..itemref import mock_ref, sign
    from ..mock import build

    which = _harno_part(level, part, task)
    seed = seed if seed is not None else secrets.randbelow(2**31)
    section = build(level, which, seed=seed,
                    content=content_db() if content_available() else None, words=db())
    body = section.to_dict() | {"seed": seed, "task": task}
    body["tasks"] = [
        q.to_page() | {"token": sign(q, mock_ref(level, which, seed=seed, index=n)
                                     | {"code": q.code, "no": q.no})}
        for n, q in enumerate(section.tasks)]
    return body


def _harno_result(level: str, part: str, res: MockResult) -> dict:
    """Grade a HARNO-format part by code and record it as exam evidence. The
    review lists every question with the answer, the key, the evidence and the
    topic behind a miss; a task type with a miss is re-tested (`mock.retests`)."""
    from ..curriculum import by_id
    from ..exam import SPECS
    from ..harnotasks import LETTERS, TYPES, check, chosen
    from ..item import fill
    from ..itemref import verify
    from ..mock import record, retests

    which = _harno_part(level, part, res.task)
    items: list[dict] = []
    seen: set[tuple] = set()
    for answer in res.answers:
        try:
            payload = verify(answer.token)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=(
                "Задание не удалось проверить: оно выдано не этим сервером.")) from exc
        ref, issued = payload["ref"], payload["item"]
        if (ref.get("kind"), ref.get("level"), ref.get("part")) != ("mock", level, which):
            raise HTTPException(status_code=400, detail="Задание из другой части.")
        if (key := (ref.get("seed"), ref.get("index"))) in seen:
            continue
        seen.add(key)
        ok = check(issued, answer.given)
        options = [o for o in (issued.get("distractor") or "").split(" | ") if o]
        topic = issued.get("topic") or ""
        try:
            topic_et = by_id(topic).et if topic else ""
        except KeyError:
            topic_et = topic
        items.append({
            "code": ref.get("code", ""), "no": ref.get("no"),
            "given": answer.given.strip(),
            "chosen": chosen(issued, answer.given) if options else "",
            "answer": issued["answer"],
            "letter": LETTERS[options.index(issued["answer"])] if issued["answer"] in options else "",
            "correct": ok,
            # The evidence: the sentence with its key, or what was heard.
            "evidence": issued.get("say") or fill(issued["prompt"], issued["answer"]),
            "mark": issued.get("hint") or "",
            "topic": topic, "topic_et": topic_et, "why_ru": issued.get("why_ru") or "",
        })
    items.sort(key=lambda i: (i["no"] is None, i["no"] or 0))

    blocks: dict[str, dict] = {}
    for i in items:
        b = blocks.setdefault(i["code"], {"code": i["code"], "asked": 0, "correct": 0,
                                          "topics": []})
        b["asked"] += 1
        b["correct"] += int(i["correct"])
        if not i["correct"] and i["topic"] and i["topic"] not in b["topics"]:
            b["topics"].append(i["topic"])
    for b in blocks.values():
        if b["code"] in TYPES:
            b |= {"no": TYPES[b["code"]].no, "et": TYPES[b["code"]].et}
    detail = {"format": "harno", "blocks": list(blocks.values())}
    if res.task is not None:
        detail["practice"] = next(iter(blocks), f"{level}-{part}{res.task}")
    saved = record(progress_db(), level, part, res.seconds, len(items),
                   sum(i["correct"] for i in items), detail=detail)
    practise = list(dict.fromkeys(i["topic"] for i in items
                                  if not i["correct"] and i["topic"]))
    return saved | {"minutes": SPECS[level].part(part).minutes, "items": items,
                    "practise": practise, "blocks": list(blocks.values()),
                    "retests": retests(progress_db(), level)}


def _exam_path(item_id: str):
    """Find a downloaded task inside the private exam mount, never outside it."""
    import json as _json
    from pathlib import Path

    from .. import config

    row = content_db().execute(
        "SELECT title, level, source_id, meta FROM items WHERE id = ?",
        (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Материал не найден.")
    try:
        meta = _json.loads(row["meta"] or "{}")
    except ValueError:
        meta = {}
    from ..library import exam_stored_path

    stored = exam_stored_path(meta, row["level"], row["source_id"])
    if not stored:
        raise HTTPException(status_code=404, detail=(
            "Этот материал не скачан — открой его по ссылке."))
    root = Path(config.EXAM_DIR).resolve()
    path = (root / stored).resolve()
    if root not in path.parents or not path.exists():
        # A meta row pointing outside the folder is a bug, not a request to obey.
        if not meta.get("file") and root in path.parents:
            raise HTTPException(status_code=404, detail=(
                "Этот материал не скачан — открой его по ссылке."))
        raise HTTPException(status_code=404, detail="Файл недоступен.")
    return path


@router.get("/api/exam/file/{item_id}")
def exam_file(item_id: str):
    """One downloaded exam file, protected by the same mount containment check."""
    from fastapi.responses import FileResponse

    path = _exam_path(item_id)
    kinds = {".pdf": "application/pdf", ".mp3": "audio/mpeg",
             ".wav": "audio/wav", ".docx":
             "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    return FileResponse(path, media_type=kinds.get(path.suffix.lower(),
                                                   "application/octet-stream"),
                        filename=path.name,
                        content_disposition_type=("inline" if path.suffix.lower() == ".pdf"
                                                  else "attachment"))


@router.get("/api/exam/pages/{item_id}")
def exam_pages(item_id: str) -> dict:
    """Page count for the app's built-in PDF reader."""
    import pypdfium2 as pdfium

    path = _exam_path(item_id)
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Это не PDF.")
    try:
        with _PDF_LOCK:
            doc = pdfium.PdfDocument(path)
            try:
                return {"pages": len(doc)}
            finally:
                doc.close()
    except pdfium.PdfiumError as exc:
        raise HTTPException(status_code=422, detail="PDF не открылся.") from exc


@router.get("/api/exam/page/{item_id}/{page}")
def exam_page(item_id: str, page: int) -> Response:
    """Render one page on demand; works even without a browser PDF viewer."""
    import io

    import pypdfium2 as pdfium

    path = _exam_path(item_id)
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Это не PDF.")
    try:
        with _PDF_LOCK:
            doc = pdfium.PdfDocument(path)
            try:
                if page < 1 or page > len(doc):
                    raise HTTPException(status_code=404, detail="Страница не найдена.")
                pdf_page = doc[page - 1]
                try:
                    bitmap = pdf_page.render(scale=1.7)
                    try:
                        out = io.BytesIO()
                        bitmap.to_pil().save(out, format="PNG")
                    finally:
                        bitmap.close()
                finally:
                    pdf_page.close()
            finally:
                doc.close()
    except pdfium.PdfiumError as exc:
        raise HTTPException(status_code=422, detail="PDF не открылся.") from exc
    return Response(out.getvalue(), media_type="image/png",
                    headers={"cache-control": "private, max-age=86400"})


@router.get("/api/exam/image/{item_id}/{page}/{index}")
def exam_image(item_id: str, page: int, index: int) -> Response:
    """One embedded PDF figure, for native cards without a PDF viewer."""
    from pathlib import Path

    from pypdf import PdfReader

    path = _exam_path(item_id)
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Это не PDF.")
    reader = PdfReader(str(path))
    if page < 1 or page > len(reader.pages):
        raise HTTPException(status_code=404, detail="Страница не найдена.")
    images = reader.pages[page - 1].images
    if index < 1 or index > len(images):
        raise HTTPException(status_code=404, detail="Изображение не найдено.")
    image = images[index - 1]
    kind = {".png": "image/png", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".gif": "image/gif"}.get(
                Path(image.name).suffix.lower())
    if not kind:
        raise HTTPException(status_code=415, detail="Формат изображения не поддерживается.")
    return Response(image.data, media_type=kind,
                    headers={"cache-control": "private, max-age=86400"})


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
        # The task exists; it simply has no extracted text (a scan, audio, a
        # .docx). An answer, not an error: a 404 here reads as a broken link.
        return {"id": item_id, "available": False,
                "note": "Текст этого задания не удалось разобрать — открой файл."}
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
            "available": True,
            "note": "Официальное задание — © Haridus- ja Noorteamet."}


@router.get("/api/exam/native/{item_id}")
def exam_native(item_id: str) -> dict:
    """Page-aware task text and reviewed controls from the private exam mount."""
    from ..exam_native import load

    path = _exam_path(item_id)
    # A task without a prepared sidecar is the usual case, not a failure: say so
    # in the answer, so the page does not log a missing resource for every task.
    if path.suffix.lower() != ".pdf":
        return {"available": False, "note": "Это не PDF."}
    draft = load(path)
    if draft is None:
        return {"available": False,
                "note": "Структурированное задание ещё не подготовлено."}
    questions = draft["questions"] if draft["verified"] else []
    return {"available": True, "pages": draft["pages"], "verified": draft["verified"],
            "kind": draft["kind"] if draft["verified"] else "none",
            "figures": draft["figures"] if draft["verified"] else [],
            "questions": [{k: v for k, v in q.items() if k != "answer"}
                          for q in questions], "note": draft["note"]}


class NativeAnswers(BaseModel):
    answers: dict[int, str]


@router.post("/api/exam/native/{item_id}/check")
def check_exam_native(item_id: str, submission: NativeAnswers) -> dict:
    """Score only a reviewed printed key. This is practice, never mastery."""
    from ..exam_native import load

    path = _exam_path(item_id)
    draft = load(path) if path.suffix.lower() == ".pdf" else None
    if not draft or not draft["verified"]:
        raise HTTPException(status_code=404, detail="Проверенный ключ недоступен.")
    questions = draft["questions"]
    wanted = {q["number"] for q in questions}
    allowed = ({"A", "B", "C"} if draft["kind"] == "multiple-choice"
               else {f["letter"] for f in draft["figures"]})
    if set(submission.answers) != wanted or any(
            answer not in allowed for answer in submission.answers.values()):
        raise HTTPException(status_code=422, detail="Ответь на все вопросы.")
    results = [{"number": q["number"], "correct":
                submission.answers[q["number"]] == q["answer"],
                "answer": q["answer"]} for q in questions]
    return {"correct": sum(r["correct"] for r in results),
            "total": len(results), "results": results,
            "note": "Официальный ключ ответа; тренировка не влияет на освоение темы."}
