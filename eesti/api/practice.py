"""Drills: the syllabus, one topic's items, and grading an answer.

Generation and grading are deterministic — no model decides whether an answer
is right or what to practise next. An empty set is a 200 with a reason, not an
error: "there is no generator for this topic yet" and "the corpus has not been
uploaded" are different states and the learner is told which.
"""


from __future__ import annotations


import sqlite3


from fastapi import APIRouter, HTTPException


from pydantic import BaseModel, Field


from ..config import LEVELS


from ..drills import generate, generate_verb_drills


from .deps import content_db, db, gloss_db, progress_db, review_db


from .render import _glosses_for, _topic_reference, reading_for


router = APIRouter()


class DrillRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=50)
    levels: list[str] = Field(default_factory=lambda: list(LEVELS))
    rules: list[str] | None = None
    seed: int | None = None


@router.post("/api/drills")
def drills(req: DrillRequest) -> dict:
    """Generate object-case drills. Fully offline."""
    try:
        # verb-form is a different generator: it drills irregular stems rather
        # than object case, so it does not share the template pool.
        if req.rules == ["verb-form"]:
            items = generate_verb_drills(
                db(), count=req.count, levels=tuple(req.levels), seed=req.seed
            )
        else:
            items = generate(
                db(),
                count=req.count,
                levels=tuple(req.levels),
                rules=tuple(req.rules) if req.rules else None,
                seed=req.seed,
            )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"drills": [d.to_dict() for d in items]}


# --------------------------------------------------------------------------
# The path: curriculum, practice, progress, placement, checkpoints
# --------------------------------------------------------------------------

class PracticeRequest(BaseModel):
    topic: str | None = None
    theme: str | None = None
    count: int = Field(default=10, ge=1, le=30)
    levels: list[str] = Field(default_factory=lambda: list(LEVELS))
    seed: int | None = None


class AnswerRequest(BaseModel):
    topic: str
    prompt: str
    answer: str
    given: str
    distractor: str = ""
    lemma: str = ""
    label: str = ""
    why_ru: str = ""


class _Answered:
    """A graded item reconstructed from the client, for recording only.

    `progress.record` and `handoff.queue_failed` need an object with these
    fields; they never regenerate the drill, so this is deliberately a plain
    carrier rather than a re-created generator item.
    """

    def __init__(self, req: "AnswerRequest") -> None:
        self.topic = req.topic
        self.prompt = req.prompt
        self.answer = req.answer
        self.distractor = req.distractor
        self.lemma = req.lemma
        self.label = req.label
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
    # `blocked_by` holds topic ids, and the page printed them straight onto the
    # screen: "astmevaheldus <- gen-stem". `gen-stem` is a database key; the
    # thing the learner has to go and study is called `omastava tüvi`, and the
    # whole point of an Estonian label here is that the term is what gets
    # learned. Eleven rows read that way.
    #
    # Resolved here rather than in the page, because this is the third time the
    # same bug has been fixed in a different place -- `kusisonad` on this very
    # panel, then `obj-case` in the review queue. A page that has to know how to
    # turn ids into names will eventually meet an id nobody taught it about.
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
                # Whether the Teema control does anything on this topic.
                #
                # It is offered beside every topic, and on seven of the
                # twenty-six drillable ones a theme is inapplicable rather than
                # ignored -- question words, comparatives, ordinals, commas,
                # word order, the rection table and obj-case have no lemma to
                # narrow. Choosing one there changed nothing, said nothing, and
                # looked exactly like choosing one that worked.
                #
                # Read from the same function the generator dispatch reads, so
                # the page cannot promise a filter the drill will not apply.
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
                "detail": "Пока нечего повторять — начни с «Rada»."}

    # `by_id` raises KeyError on a topic that does not exist, and this lookup
    # sits above the try/except that used to catch it -- so moving it here
    # turned an unknown topic from a 400 into a 500. Guarded on its own, since
    # "no such topic" is a different answer from "no generator for it".
    try:
        meta = by_id(topic)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"no such topic: {topic}") from exc

    # 13 of the 36 topics have no generator. They are in the syllabus and in
    # the path, so practising them is a thing a learner will try, and what came
    # back was a 400 carrying a Python exception message:
    #
    #     'tahestik' has no generator — see step 2 of docs/curriculum-plan.md
    #
    # English, naming a file the learner does not have, rendered by the page as
    # "Viga: ...". Two rules broken at once -- explanations are in Russian, and
    # a message nobody can read is not a message.
    #
    # It is also not an error. The request was valid and the answer is "there
    # is no exercise for this yet", which is the same shape as a topic whose
    # corpus has not been uploaded: 200, no items, and a reason. That lets the
    # page keep offering the EKK reference, so the topic still teaches
    # something instead of dead-ending.
    if meta.generator is None:
        reference = _topic_reference(meta)
        # Only 1 of the 13 (`astmevaheldus`) carries an EKK reference, so the
        # sentence has to be conditional. Promising "the rule is linked below"
        # with nothing below it is a worse message than the English one it
        # replaced -- it sends the learner looking for something that is not
        # there.
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

    from ..practice import theme_slot

    try:
        items = items_for(
            topic, count=req.count, levels=tuple(req.levels), seed=req.seed,
            theme=req.theme,
        )
    except (ValueError, RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # An empty list is not self-explanatory, and the page can only print what
    # it is given: without a reason it showed a bare "midagi ei tulnud".
    #
    # The generators that draw on the harvested corpus produce nothing when the
    # corpus has not been supplied, which is a supported state and a completely
    # different problem from a generator that is broken. Say which it is, and
    # in Russian, because it is an instruction the learner has to act on.
    #
    # Three reasons for an empty list, and they need three different sentences.
    # The word theme is the one that was missing, and it is the commonest:
    # measured across the whole grid, **31 of 198 topic x theme pairs return
    # fewer than three items and 6 return none**, because a corpus cloze needs
    # a sentence that contains a theme noun, which is much rarer than the noun
    # existing. The learner was told the generator had failed, which is untrue
    # and unactionable -- the fix is one click, without the theme.
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
        # What was actually applied. The page guards the control now, but the
        # contract must answer for itself: a caller that sends a theme to a
        # closed-class topic had no way to learn it was dropped.
        "theme": req.theme if (req.theme and theme_slot(topic)) else None,
        "reference": _topic_reference(meta),
        "items": [i.to_dict() for i in items],
        # What the words in this set mean, from the local store only.
        #
        # A B1 object-case set comes back on lemmas like `etendus`, `luuletus`
        # and `rahakott`. A learner can inflect those correctly without knowing
        # one of them, and then has practised morphology on a token -- which is
        # half of what the exercise looks like it is teaching.
        #
        # Local reads only: a live lookup per item would be the batch request
        # `sonapi` refuses to have a helper for, and would make a practice set
        # wait on a third party. Words not yet stored are simply not glossed,
        # and get filled one at a time as each item is answered.
        "glosses": _glosses_for([i.lemma for i in items]),
        # Something to read that is *about* this contrast, not merely at this
        # level. This is the join that makes practice and the reading library
        # one tool: a drill teaches the rule, a text shows it being used.
        "reading": reading_for(topic),
    }


@router.post("/api/practice/answer")
def practice_answer(req: AnswerRequest) -> dict:
    """Grade one answer, record it, and queue it for review if it was missed."""
    from ..handoff import queue_failed
    from ..progress import (MASTERY_CORRECT, MASTERY_WINDOW, accuracy,
                           is_mastered, record)

    item = _Answered(req)
    correct = item.check(req.given)
    progress = progress_db()
    was_mastered = is_mastered(progress, req.topic)
    record(progress, item, correct, answer=req.given)

    if not correct:
        try:
            queue_failed(review_db(), item)
        except Exception:  # noqa: BLE001 - review is enrichment, never a blocker
            pass

    mastered_now = is_mastered(progress, req.topic)
    if mastered_now and not was_mastered:
        from ..handoff import seed_mastered

        seed_mastered(review_db(), req.topic)

    # One lookup, for the one word the learner just spent thought on. This is
    # the "word in front of the learner" case `sonapi` exists for, and it is
    # also the right moment pedagogically: the meaning lands straight after the
    # struggle with the form, not before it as a hint.
    meaning: list[str] = []
    if req.lemma:
        from .. import gloss

        try:
            kept = gloss.remember(gloss_db(), req.lemma)
            meaning = list(kept.russian) if kept else []
        except Exception:  # noqa: BLE001 - a gloss is never worth failing a grade
            meaning = []

    return {
        "correct": correct,
        "answer": req.answer,
        "why_ru": req.why_ru,
        "russian": meaning,
        "accuracy": accuracy(progress, req.topic),
        "mastered": mastered_now,
        "just_mastered": mastered_now and not was_mastered,
        "gate": f"{MASTERY_CORRECT}/{MASTERY_WINDOW}",
    }
