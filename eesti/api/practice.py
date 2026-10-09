"""Drills: the syllabus, one topic's items, and grading an answer.

Generation and grading are deterministic — no model decides whether an answer
is right or what to practise next. An empty set is a 200 with a reason, not an
error: "there is no generator for this topic yet" and "the corpus has not been
uploaded" are different states and the learner is told which.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from pydantic import BaseModel, Field

from ..config import LEVELS

from .deps import content_db, db, gloss_db, progress_db, review_db

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
    # Answered offline: when it happened, and the id the page gave it. The id
    # makes sending the queue twice harmless (`eesti/evidence.py`).
    at: str = ""
    event_id: str = ""
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
            self.source_id = issued.get("source_id", "")
            self.say = issued.get("say", "")
            return
        self.topic = req.topic
        self.prompt = req.prompt
        self.answer = req.answer
        self.distractor = req.distractor
        self.lemma = req.lemma
        self.label = req.label
        self.rule = req.rule
        self.why_ru = req.why_ru
        self.source_id = ""
        self.say = ""

    def check(self, given: str) -> bool:
        from ..item import accepts

        return accepts(self.answer, given)


def _units(rows, now_topic: str | None) -> list[dict]:
    """The course's units over the learner's topic states (`eesti/units.py`).

    A unit reports how many of its core topics are mastered; it is not called
    complete, because its unit check is not built (`docs/course-structure.md`).
    """
    from .. import units
    from ..meaning import russian_many

    from ..unitcheck import parts, passed_units

    state = {r.topic: r.state for r in rows}
    current = units.home(now_topic).id if now_topic else None
    checked = passed_units(progress_db())
    out = []
    for u in units.UNITS:
        lemmas = units.words_for(u) if u.words == "algus" else ()
        meanings = russian_many(db(), gloss_db(), list(lemmas)) if lemmas else {}
        out.append({
            "id": u.id, "n": u.n, "et": u.et, "stage": u.stage, "goal_ru": u.goal_ru,
            "topics": list(u.topics),
            "mastered": sum(state.get(t) == "mastered" for t in u.topics),
            # Moved past: something skipped and nothing left to learn.
            "skipped": any(state.get(t) == "skipped" for t in u.topics) and all(
                state.get(t) in ("skipped", "mastered", "reference") for t in u.topics),
            "revisits": [{"topic": r.topic, "rules": list(r.rules), "note_ru": r.note_ru}
                         for r in u.revisits],
            "harno": list(u.harno),
            "course": f"{'Keeleklikk' if u.course[0] == 'KK' else 'Keeletee'} {u.course[1]}"
                      if u.course else None,
            "course_url": units.course_link(u, "ru"),
            "checkpoint": u.checkpoint,
            # The checked half of completion (`eesti/unitcheck.py`); a unit with
            # nothing drillable has no check and is never called complete.
            "checkable": bool(parts(u)),
            "checked": u.id in checked,
            "complete": u.id in checked and all(
                state.get(t) in ("mastered", "reference") for t in u.topics),
            "words": [{"et": w, "ru": meanings.get(w, [])[:2]} for w in lemmas],
            "pictures_url": units.PICTURES_URL if lemmas else None,
            "current": u.id == current,
        })
    return out


class UnitCheckAnswers(BaseModel):
    seed: int
    given: list[str] = Field(min_length=1, max_length=60)


def _unit(unit_id: str):
    from ..units import by_id

    try:
        return by_id(unit_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"no such unit: {unit_id}") from exc


@router.get("/api/units/{unit_id}/check")
def unit_check_items(unit_id: str, seed: int | None = None) -> dict:
    """A unit's check: five items per core topic and per revisited rule, or the
    stage checkpoint for a revision unit (`eesti/unitcheck.py`)."""
    import secrets

    from ..curriculum import by_id as topic
    from ..unitcheck import PART_PASS, PER_PART, build, parts

    unit = _unit(unit_id)
    asked = parts(unit)
    if not asked:
        raise HTTPException(status_code=400, detail=(
            "В этом блоке пока нечего проверять: у его тем нет заданий."))
    seed = seed if seed is not None else secrets.randbelow(2**31)
    try:
        items = build(unit, seed)
    except (ValueError, RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "unit": unit.id, "et": unit.et, "seed": seed,
        "parts": [{"topic": t, "rules": list(r) if r else None,
                   "et": (topic(t).et if not t.startswith("checkpoint:")
                          else f"Kontrolltöö {t.split(':', 1)[1]}")} for t, r in asked],
        "items": [item_for_page(i) for _, i in items],
        "glosses": _glosses_for([i.lemma for _, i in items]),
        "note": (f"По {PER_PART} заданий на каждую тему блока; нужно не меньше "
                 f"{PART_PASS} из {PER_PART} в каждой. Ошибка ничего не отнимает."),
    }


@router.post("/api/units/{unit_id}/check")
def unit_check_result(unit_id: str, req: UnitCheckAnswers) -> dict:
    """Grade a unit check: the server rebuilds the set from the seed."""
    from .. import config
    from ..review import connect as review_connect
    from ..unitcheck import grade

    unit = _unit(unit_id)
    try:
        return grade(progress_db(), unit, req.seed, req.given,
                     reviews=review_connect(config.learner_db("REVIEW_DB")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    from ..curriculum import TOPICS

    # How a Russian-speaking learner looks for the topic: shown as its gloss.
    russian = {t.id: t.ru for t in TOPICS}
    from ..progress import MASTERY_CORRECT, MASTERY_WINDOW, recent

    now_topic = resume(progress)
    return {
        "resume": now_topic,
        # The gate the resume topic is working towards, and its last answers in
        # order, oldest first: drawn as the gate's ten slots in the hero.
        "gate": {"correct": MASTERY_CORRECT, "window": MASTERY_WINDOW},
        "resume_recent": ([bool(x) for x in recent(progress, now_topic, MASTERY_WINDOW)]
                          if now_topic else []),
        "mastered": sum(1 for r in rows if r.state == "mastered"),
        "total": len(rows),
        "topics": [
            {
                "id": r.topic, "level": r.level, "et": r.et,
                "ru": russian.get(r.topic, ""), "state": r.state,
                "attempts": r.attempts, "accuracy": r.accuracy,
                "drillable": r.drillable, "skipped": r.skipped,
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
        "units": _units(rows, now_topic),
    }


class TopicSkip(BaseModel):
    skip: bool = True


@router.post("/api/course/topics/{topic}/skip")
def skip_topic(topic: str, req: TopicSkip) -> dict:
    """Move past a topic, or put it back, without asserting knowledge."""
    from ..course import set_skip

    try:
        set_skip(progress_db(), topic, req.skip)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Такой темы нет.") from exc
    return curriculum_path()


class UnitsSkip(BaseModel):
    units: list[str]
    skip: bool = True


@router.post("/api/course/units/skip")
def skip_units(req: UnitsSkip) -> dict:
    """Move past units — one, a run before a chosen unit, a stage — or put them
    back, without asserting knowledge."""
    from ..course import set_units_skip

    try:
        set_units_skip(progress_db(), req.units, req.skip)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Такого блока нет.") from exc
    return curriculum_path()


@router.get("/api/lesson/{topic}")
def topic_lesson(topic: str) -> dict:
    """The Reegel page for one topic (`eesti/lessons.py`)."""
    from .. import evidence
    from ..lessons import lesson

    try:
        content = content_db()
    except Exception:  # noqa: BLE001 - no corpus means no reading links, not no lesson
        content = None
    with evidence.connect() as log:
        found = lesson(topic, log=log, content=content, words=db())
    if found is None:
        raise HTTPException(status_code=404, detail="Такой темы нет.")
    return found


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
                "сервер. Выбери другую тему в курсе или открой правило."
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
    if req.event_id:
        from .. import evidence

        with evidence.connect() as log:
            if evidence.has(log, req.event_id):
                # Already recorded — the page is sending its offline queue again.
                return {"correct": correct, "event_id": req.event_id,
                        "answer": item.answer, "why_ru": item.why_ru,
                        "russian": [], "accuracy": None, "mastered": False,
                        "just_mastered": False, "recorded": False,
                        "gate": f"{MASTERY_CORRECT}/{MASTERY_WINDOW}"}

    progress = progress_db()
    topic = item.topic
    was_mastered = is_mastered(progress, topic)
    event_id = record(progress, item, correct, answer=req.given, ref=ref,
                      latency_ms=req.latency_ms,
                      mode=ref["kind"] if ref else "path",
                      at=req.at or None, event_id=req.event_id or None)

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
        # The attempt as the log knows it, so the page can ask the tutor about
        # this one rather than about the topic in general.
        "event_id": event_id,
        "answer": item.answer,
        "why_ru": item.why_ru,
        "russian": meaning,
        "accuracy": accuracy(progress, topic),
        "mastered": mastered_now,
        "just_mastered": mastered_now and not was_mastered,
        "gate": f"{MASTERY_CORRECT}/{MASTERY_WINDOW}",
    }


@router.get("/api/plan")
def todays_plan(minutes: int = 20) -> dict:
    """Today's plan: blocks in order, each with its minutes, action and Russian
    reason (`eesti/planning.py`). Deterministic for the same evidence and day."""
    from ..planning import issue

    return issue(max(5, min(minutes, 120))).to_dict()


# --------------------------------------------------------------------------
# Test-out: skip a topic you already know
# --------------------------------------------------------------------------

@router.get("/api/testout/{topic}")
def testout_items(topic: str, seed: int | None = None) -> dict:
    """Five items for a test-out. All five right marks the topic known."""
    import secrets

    from ..curriculum import by_id
    from ..placement import PROBE_ITEMS, PROBE_REQUIRED
    from ..practice import items_for

    try:
        meta = by_id(topic)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"no such topic: {topic}") from exc
    if meta.generator is None:
        raise HTTPException(status_code=400, detail=(
            "По этой теме нет заданий — её нельзя сдать экстерном."))
    seed = seed if seed is not None else secrets.randbelow(2**31)
    try:
        items = items_for(topic, count=PROBE_ITEMS, seed=seed)
    except (ValueError, RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "topic": topic, "et": meta.et, "seed": seed, "required": PROBE_REQUIRED,
        "items": [item_for_page(i) for i in items],
        "glosses": _glosses_for([i.lemma for i in items]),
        "note": ("Пять заданий. Все пять верно — тема засчитывается и "
                 "открывает следующие; ошибка ничего не отнимает."),
    }


class TestOut(BaseModel):
    seed: int
    given: list[str] = Field(min_length=1, max_length=10)


@router.get("/api/placement/next")
def placement_next(seen: str = "", failed: str = "",
                   limit: int = Query(3, ge=1, le=12)) -> dict:
    """A bounded grammar entry assessment using the existing five-item probes.

    Client history only chooses what to show. Actual passes are server-graded
    test-outs; this endpoint never awards mastery or a certified CEFR level.
    """
    from ..curriculum import TOPICS, unlocks
    from ..placement import MAX_FAILURES, candidates

    identities = {topic.id for topic in TOPICS}
    attempted = set(seen.split(",")) & identities
    misses = set(failed.split(",")) & attempted
    pruned = set().union(*(set(unlocks(topic)) for topic in misses)) if misses else set()
    pending = [topic for topic in candidates(progress_db())
               if topic.id not in attempted and topic.id not in pruned]
    done = len(attempted) >= limit or len(misses) >= MAX_FAILURES or not pending
    entries = [topic for topic in TOPICS if topic.id in misses]
    entry = entries[0] if entries else (pending[0] if pending else None)
    return {
        "done": done,
        "next": None if done else testout_items(pending[0].id),
        "entry": ({"id": entry.id, "et": entry.et, "ru": entry.ru,
                   "band": {"A1": "a1", "A2": "a2", "B1": "a2-b1"}[entry.level]}
                  if entry else None),
        "limit": limit,
        "note": "Это точка входа в грамматику, а не подтверждение уровня CEFR.",
    }


@router.get("/api/learning/sentences")
def learning_sentences(topic: str = "olevik", seed: int = 0) -> dict:
    """Short, app-generated sentences for reading, listening and read-aloud.

    This starter remains usable without an imported corpus. Forms and sentence
    frames are the existing deterministic drills, with the rule source attached.
    """
    from ..curriculum import by_id
    from ..lessons import examples

    try:
        meta = by_id(topic)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Такой темы нет.") from exc
    return {
        "topic": topic, "et": meta.et, "ru": meta.ru,
        "sentences": [row["before"] + row["answer"] + row["after"]
                      for row in examples(topic, count=5, seed=seed)],
        "source": "Genereeritud harjutused",
        "source_id": "generated",
        "reference": _topic_reference(meta),
        "note": "Учебные предложения приложения; формы проверены Vabamorf/EKI.",
    }


@router.post("/api/testout/{topic}")
def testout_result(topic: str, req: TestOut) -> dict:
    """Grade a test-out: the server rebuilds the same items from the seed and
    runs the same probe the CLI does (`eesti/placement.py`)."""
    from ..placement import PROBE_ITEMS, probe

    if len(req.given) != PROBE_ITEMS:
        raise HTTPException(status_code=400,
                            detail=f"ожидается {PROBE_ITEMS} ответов")
    answers = iter(req.given)
    result = probe(progress_db(), topic, lambda item: next(answers), seed=req.seed)
    return {"topic": result.topic, "asked": result.asked, "correct": result.correct,
            "passed": result.passed, "skipped": result.skipped,
            # What was wrong and what was expected, item by item.
            "items": list(result.items)}


@router.get("/api/pack")
def offline_pack(count: int = 24) -> dict:
    """A set to practise with no connection: items, their answers, their glosses.

    The page keeps it and grades against the answer it already holds, because
    offline there is nobody to ask. What was answered is sent back when the
    connection returns and **re-graded from the token** — the server still
    decides, only later (`docs/app-structure.md`).
    """
    import secrets
    from datetime import datetime, timezone

    from .. import config
    from ..itemref import practice_ref, sign
    from ..learner import rule_evidence, weak_rules
    from ..practice import items_for
    from ..progress import resume
    from ..review import connect as review_connect

    from ..curriculum import by_id
    from ..practice import HEARD
    from ..progress import report

    count = max(4, min(count, 60))
    progress = progress_db()

    def written(topic: str) -> bool:
        """Answerable without a recording: heard items need a connection."""
        return by_id(topic).generator not in HEARD

    topics: list[str] = []
    here = resume(progress)
    if here and written(here):
        topics.append(here)
    weak = weak_rules(rule_evidence(
        progress, review_connect(config.learner_db("REVIEW_DB"))))
    topics += [e.topic for e in weak if e.topic not in topics and written(e.topic)][:2]
    if not topics:
        # The next topic that can be answered in writing.
        topics = [r.topic for r in report(progress)
                  if r.state in ("ready", "in progress") and r.drillable
                  and written(r.topic)][:1] or ["kusisonad"]

    per = max(2, count // len(topics))
    items, glosses = [], {}
    for topic in topics:
        seed = secrets.randbelow(2**31)
        try:
            made = items_for(topic, count=per, seed=seed)
        except (ValueError, RuntimeError, KeyError):
            continue
        for n, item in enumerate(made):
            # An item that is heard needs the recording, and offline there is
            # nobody to fetch it from.
            if getattr(item, "say", ""):
                continue
            items.append(item_for_page(item) | {
                "topic": topic,
                "token": sign(item, practice_ref(
                    topic, seed=seed, count=per, levels=list(LEVELS),
                    theme=None, rules=None, index=n)),
            })
        glosses |= _glosses_for([i.lemma for i in made])

    return {
        "issued": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "topics": topics,
        "items": items[:count],
        "glosses": glosses,
        "note": ("Набор для работы без интернета. Ответы записываются на "
                 "сервере, когда связь вернётся."),
    }
