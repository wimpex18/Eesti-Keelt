"""Drills: the syllabus, one topic's items, and grading an answer.

Generation and grading are deterministic — no model decides whether an answer
is right or what to practise next. An empty set is a 200 with a reason, not an
error: "there is no generator for this topic yet" and "the corpus has not been
uploaded" are different states and the learner is told which.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field

from ..config import LEVELS

from .deps import db, gloss_db, progress_db, review_db

from .render import _glosses_for, _topic_reference, item_for_page, reading_for


router = APIRouter()


# --------------------------------------------------------------------------
# The path: curriculum, practice, progress, placement, checkpoints
# --------------------------------------------------------------------------

class PracticeRequest(BaseModel):
    topic: str | None = None
    theme: str | None = None
    count: int = Field(default=10, ge=1, le=30)
    levels: list[str] = Field(default_factory=lambda: list(LEVELS))
    seed: int | None = None
    # Object-case sub-rules (`negation`, `completed`, `ongoing`) for free practice on
    # the #1 weakness. Only `obj-case` reads it; other topics ignore it.
    rules: list[str] | None = None


class AnswerRequest(BaseModel):
    topic: str
    prompt: str
    answer: str
    given: str
    distractor: str = ""
    lemma: str = ""
    label: str = ""
    # The item's sub-rule, where its generator has one (`obj-case`, `gen-stem`).
    rule: str = ""
    why_ru: str = ""
    # The signed item the server issued (`eesti/itemref.py`). When present, the
    # item is graded from it and the fields above are ignored.
    token: str = ""
    # How long the learner took, from showing the item to answering.
    latency_ms: int | None = Field(default=None, ge=0)
    # Free practice (Rada's "Vaba harjutus") is graded here by the same rule but
    # leaves no trace: no attempt, no mastery, no review card.
    record: bool = True


class _Answered:
    """A graded item reconstructed from the client, for recording only (fields that
    `progress.record` and `handoff.queue_failed` read).
    """

    def __init__(self, req: "AnswerRequest", issued: dict | None = None) -> None:
        if issued is not None:
            # What the server signed; the page's copy of the answer is not read.
            self.topic = issued["topic"]
            self.prompt = issued["prompt"]
            self.answer = issued["answer"]
            self.distractor = issued["distractor"]
            self.lemma = issued["lemma"]
            self.label = issued["hint"]
            self.rule = issued["rule"]
            self.why_ru = issued["why_ru"]
            return
        self.topic = req.topic
        self.prompt = req.prompt
        self.answer = req.answer
        self.distractor = req.distractor
        self.lemma = req.lemma
        self.label = req.label
        self.rule = req.rule
        self.why_ru = req.why_ru

    def check(self, given: str) -> bool:
        return given.strip().casefold() == self.answer.casefold()


@router.get("/api/curriculum")
def curriculum_path() -> dict:
    """The whole syllabus in study order, with where the learner stands on each."""
    from ..practice import theme_slot
    from ..progress import report, resume

    progress = progress_db()
    rows = report(progress)
    # Resolve `blocked_by` topic ids to Estonian names (`omastava tüvi`, not
    # `gen-stem`) here, so no page prints a database key.
    names = {r.topic: r.et for r in rows}
    return {
        "resume": resume(progress),
        "mastered": sum(1 for r in rows if r.state == "mastered"),
        "total": len(rows),
        "topics": [
            {
                "id": r.topic, "level": r.level, "et": r.et, "state": r.state,
                "attempts": r.attempts, "accuracy": r.accuracy,
                # Ids kept as well: the page needs them to link, and a caller
                # that wants to match on identity must not have to reverse a
                # display string to get it back.
                "blocked_by": [names.get(b, b) for b in r.blocked_by],
                "blocked_by_ids": list(r.blocked_by),
                # Whether the Teema control applies to this topic; closed-class topics have no
                # lemma to narrow. Read from the same function the generator dispatch uses.
                "themed": theme_slot(r.topic) is not None if r.drillable else False,
            }
            for r in rows
        ],
    }


@router.get("/api/themes")
def themes_list() -> dict:
    from ..themes import coverage

    return {"themes": [{"id": k, **v} for k, v in coverage(db()).items()]}


@router.post("/api/practice")
def practice_items(req: PracticeRequest) -> dict:
    """Items for one topic — the topic you are on, unless you name another."""
    from ..curriculum import by_id
    from ..practice import items_for
    from ..progress import resume

    topic = req.topic or resume(progress_db())
    if topic is None:
        return {"topic": None, "items": [],
                "detail": "Все открытые темы пройдены. Их можно повторить в "
                          "«Vaba harjutus», а весь список — в «Kogu rada»."}

    # An unknown topic is a 400, distinct from a topic with no generator.
    try:
        meta = by_id(topic)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"no such topic: {topic}") from exc

    # A topic with no generator is a valid request: answer 200 with no items and a
    # Russian reason, so the page can still offer the EKK reference.
    if meta.generator is None:
        reference = _topic_reference(meta)
        # Only some of those topics have an EKK reference, so the sentence is conditional.
        detail = (
            "Упражнений по этой теме пока нет — она есть в программе, но "
            "генератор для неё ещё не написан."
        )
        if reference and reference.get("known"):
            detail += " Правило можно прочитать по ссылке ниже."
        return {
            "topic": topic, "level": meta.level, "et": meta.et, "ru": meta.ru,
            "items": [], "detail": detail, "reference": reference, "glosses": {},
        }

    import secrets

    from ..itemref import practice_ref, sign
    from ..practice import theme_slot

    # A set is always seeded, so every item in it can be generated again.
    seed = req.seed if req.seed is not None else secrets.randbelow(2**31)
    rules = tuple(req.rules) if req.rules else None
    try:
        items = items_for(
            topic, count=req.count, levels=tuple(req.levels), seed=seed,
            theme=req.theme, rules=rules,
        )
    except (ValueError, RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # An empty list gets a Russian reason the learner can act on: no generator, no
    # corpus uploaded, or the chosen theme leaves too few sentences.
    detail = None
    theme_emptied = False
    if not items:
        needs_corpus = meta.generator in ("corpus_cloze", "ekk_rection", "wordorder")
        if req.theme and theme_slot(topic):
            theme_emptied = True
            detail = (
                "По этой словарной теме заданий не нашлось — слов темы в "
                "нужной форме слишком мало. Правило то же, попробуй без темы."
            )
        elif needs_corpus:
            detail = (
                "Для этой темы нужен текстовый корпус, а он ещё не загружен на "
                "сервер — задания появятся после `deploy/push-content.sh`."
            )
        else:
            detail = f"Генератор «{meta.generator}» ничего не вернул для этой темы."

    return {
        "topic": topic,
        "level": meta.level,
        "et": meta.et,
        "ru": meta.ru,
        "detail": detail,
        # Whether the word theme is what emptied the set, so the page can offer
        # the retry rather than leave the learner to guess which of the three
        # controls to change.
        "theme_emptied": theme_emptied,
        # Report the theme actually applied, so a caller learns when it was dropped.
        "theme": req.theme if (req.theme and theme_slot(topic)) else None,
        "reference": _topic_reference(meta),
        "items": [
            item_for_page(i) | {"token": sign(i, practice_ref(
                topic, seed=seed, count=req.count, levels=req.levels,
                theme=req.theme, rules=rules, index=n))}
            for n, i in enumerate(items)
        ],
        # Meanings of the set's words from the local store only — never a live lookup per
        # item. Unstored words are glossed as each item is answered.
        "glosses": _glosses_for([i.lemma for i in items]),
        # Something to read that is *about* this contrast, not merely at this
        # level. This is the join that makes practice and the reading library
        # one tool: a drill teaches the rule, a text shows it being used.
        "reading": reading_for(topic),
    }


@router.post("/api/practice/answer")
def practice_answer(req: AnswerRequest) -> dict:
    """Grade one answer, record it, and queue it for review if it was missed.

    With `record: false` the answer is only graded: free practice must not move the
    mastery gate or fill the review queue.
    """
    from ..handoff import queue_failed, review_correct
    from ..progress import (MASTERY_CORRECT, MASTERY_WINDOW, accuracy,
                           is_mastered, record)

    ref = None
    if req.token:
        from ..itemref import verify

        try:
            issued = verify(req.token)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=(
                "Задание не удалось проверить: оно выдано не этим сервером или "
                "устарело. Открой новый набор.")) from exc
        item, ref = _Answered(req, issued["item"]), issued["ref"]
    else:
        item = _Answered(req)
    correct = item.check(req.given)
    if not req.record:
        return {
            "correct": correct, "answer": item.answer, "why_ru": item.why_ru,
            "russian": [], "accuracy": None, "mastered": False,
            "just_mastered": False, "gate": f"{MASTERY_CORRECT}/{MASTERY_WINDOW}",
        }
    progress = progress_db()
    topic = item.topic
    was_mastered = is_mastered(progress, topic)
    record(progress, item, correct, answer=req.given, ref=ref,
           latency_ms=req.latency_ms,
           mode=ref["kind"] if ref else "path")

    try:
        if correct:
            # A card already in the queue and due counts this as its review.
            review_correct(review_db(), item, latency_ms=req.latency_ms)
        else:
            queue_failed(review_db(), item)
    except Exception:  # noqa: BLE001 - review is enrichment, never a blocker
        pass

    mastered_now = is_mastered(progress, topic)
    if mastered_now and not was_mastered:
        from ..handoff import seed_mastered

        seed_mastered(review_db(), topic)

    # One live lookup for the word just answered: the meaning lands right after the
    # learner worked on the form.
    meaning: list[str] = []
    if item.lemma:
        from .. import gloss
        from ..meaning import russian

        # EKI's dictionary answers most words, and then no request is spent.
        meaning, source = russian(db(), item.lemma)
        try:
            if source not in ("seed", "eki-evs"):
                kept = gloss.remember(gloss_db(), item.lemma)
                meaning, _ = russian(db(), item.lemma, kept.russian if kept else ())
        except Exception:  # noqa: BLE001 - a gloss is never worth failing a grade
            pass

    return {
        "correct": correct,
        "answer": item.answer,
        "why_ru": item.why_ru,
        "russian": meaning,
        "accuracy": accuracy(progress, topic),
        "mastered": mastered_now,
        "just_mastered": mastered_now and not was_mastered,
        "gate": f"{MASTERY_CORRECT}/{MASTERY_WINDOW}",
    }
