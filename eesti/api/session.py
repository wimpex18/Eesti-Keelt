"""The session (ADR-0009): Täna, its steps, answering them, and Haiku's help.

What the page receives never holds an answer key: an item comes with its
token, its choices where it is a choice, and the form it asks for moved to
`form_after` where naming it would answer it (DESIGN.md: a form is named under
the word only after the attempt). The key, the reason and the form's name come
back with the verdict.

**Only the first attempt counts.** `/api/session/answer` records an item's
first attempt through the practice path (`api.practice.practice_answer`): the
attempt, mastery, the review card a miss makes. A first miss in a step that
allows it (`session.RETRY_STEPS`, a typed item) comes back with a hint from
code instead of the key, and the retry is graded with `record: false`.

Haiku (ADR-0008) explains a miss (*Miks?*), answers a question on the rule
page and comments on writing and speaking against HARNO's descriptors after
code's checklist; its words carry their engine and decide nothing.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import LEVELS

from .deps import db, progress_db, review_db
from .render import _glosses_for, item_for_page

router = APIRouter()

#: Fields that would answer an item before it is attempted.
_KEYS = ("answer", "distractor", "why_ru", "solution")

#: Labels that name the task (unit 1's), not a form: never withheld, and never
#: a form line's name.
TASK_LABELS = frozenset({"sõnadega", "numbritega", "kuula", "fraas", "vastus", "küsisõna"})


def _known_word(form: str) -> bool:
    """Every word of a choice is one Vabamorf knows (a choice is never a non-word)."""
    from ..morph import _readings

    try:
        return all(_readings(w) for w in form.replace("?", " ").replace("!", " ").split())
    except Exception:  # noqa: BLE001 - no morphology: offer no choice
        return False


def page_item(item, ref: dict, *, choice: bool = False, withhold: bool = False) -> dict:
    """An item as the session shows it: signed, keyed by nothing the page holds.

    `choice` offers the key and the generator's other form, sorted, where both
    are words; `withhold` moves the form asked for to `form_after`."""
    from ..itemref import sign

    shown = item_for_page(item) | {"token": sign(item, ref)}
    if withhold and shown.get("label") and shown["label"] not in TASK_LABELS:
        shown["form_after"], shown["label"] = shown["label"], ""
    if choice and not shown.get("choices") and not shown.get("tiles"):
        key = (item.answer or "").split(" ~ ")[0].strip()
        other = (item.distractor or "").strip()
        if key and other and other.casefold() != key.casefold() and _known_word(other) \
                and _known_word(key):
            shown["choices"] = sorted({key, other}, key=str.casefold)
    for name in _KEYS:
        shown.pop(name, None)
    shown["typed"] = not shown.get("choices") and not shown.get("tiles")
    return shown


def _items(topic: str, count: int, seed: int, rules=None, **kw) -> list[dict]:
    from ..itemref import practice_ref
    from ..practice import items_for

    try:
        made = items_for(topic, count=count, levels=LEVELS, seed=seed, rules=rules)
    except (ValueError, RuntimeError, KeyError):
        return []
    return [page_item(item, practice_ref(topic, seed=seed, count=count, levels=LEVELS,
                                         theme=None, rules=rules, index=n), **kw)
            for n, item in enumerate(made)]


def _session(topic: str | None = None):
    from .. import session

    inputs = session.gather(topic=topic)
    return inputs, session.compose(inputs)


# --------------------------------------------------------------------------
# Täna and the session
# --------------------------------------------------------------------------

@router.get("/api/session")
def session_today() -> dict:
    """Täna: today's session, its plan, the next task and the hero."""
    from .. import session

    return session.today()


@router.post("/api/session/start")
def session_start() -> dict:
    """Start today's session (once a day; later calls return the same one)."""
    from .. import session

    return session.start()


@router.get("/api/session/topic/{topic}")
def session_topic(topic: str) -> dict:
    """A session on one topic: its rule, practice and a short check."""
    from .. import session
    from ..curriculum import by_id

    try:
        by_id(topic)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Такой темы нет.") from exc
    inputs, made = _session(topic)
    return {"session": made.to_dict(), "next": session.next_task(inputs, made)}


@router.get("/api/session/step/{step}")
def session_step(step: str, topic: str | None = None) -> dict:
    """One step's content, generated again from the session's seed, so a reload
    shows the same items."""
    from .. import session

    inputs, made = _session(topic)
    found = made.step(step)
    if found is None:
        raise HTTPException(status_code=404, detail="Такого шага сегодня нет.")
    seed = session.seed_of(made.id, step)
    body = {"session": made.id, "step": step, "et": found.et, "ru": found.ru,
            "why_ru": found.why_ru, "count": found.count}
    builder = _BUILDERS[step]
    return body | builder(inputs, made, found, seed)


def _review(inputs, made, step, seed) -> dict:
    """Due cards and yesterday's misses, mixed; graded cards are answered by code
    (typed or chosen), meaning cards rated by the learner."""
    from datetime import datetime, timezone

    from .. import evidence, evs, review, session
    from ..licences import credit
    from .render import _topic_name

    rev = review_db()
    now = datetime.now(timezone.utc)
    cards = review.due(rev, limit=step.count)
    if len(cards) < step.count:
        with evidence.connect() as log:
            extra = session._yesterday(log, rev, session.local_day(now), now)
        have = {c.id for c in cards}
        rows = [r for r in rev.execute(
            f"SELECT * FROM review_items WHERE id IN ({','.join('?' * len(extra))})",  # noqa: S608
            extra)] if extra else []
        for r in rows:
            if r["id"] in have or len(cards) >= step.count:
                continue
            cards.append(review.ReviewItem(
                id=r["id"], kind=r["kind"], lemma=r["lemma"], prompt=r["prompt"],
                answer=r["answer"], distractor=r["distractor"], why_ru=r["why_ru"],
                context=r["context"], due=datetime.fromisoformat(r["due"]),
                reps=r["reps"], lapses=r["lapses"], source_id=r["source_id"]))
    words = db() if any(c.kind == "vocab" for c in cards) else None
    out = []
    for c in cards:
        shown = {"id": c.id, "kind": c.kind, "kind_et": _topic_name(c.kind),
                 "lemma": c.lemma, "prompt": c.prompt, "context": c.context,
                 "reps": c.reps, "lapses": c.lapses, "attribution": credit(c.source_id)}
        if c.kind == "vocab":
            # A meaning card is rated by the learner: the meaning is its back.
            shown |= {"meaning": c.answer,
                      "phrase": evs.practice_phrase(words, c.lemma, c.reps)}
        else:
            key = c.answer.split(" ~ ")[0]
            if c.distractor and c.distractor.casefold() != key.casefold():
                shown["choices"] = sorted({key, c.distractor}, key=str.casefold)
            shown["typed"] = "choices" not in shown
        out.append(shown)
    return {"kind": "cards", "cards": out, "glosses": _glosses_for([c.lemma for c in cards])}


def _rule(inputs, made, step, seed) -> dict:
    """Rule by doing: the forms to notice, then items chosen between two forms
    with the form not named, then the rule from its sources (shown after)."""
    from .. import session
    from ..lessons import lesson
    from ..rulewalk import walk

    topic = made.topic
    items: list[dict] = []
    walked = walk(topic, words=db(), seed=seed) if inputs.walk else None
    if walked:
        # The walk's own ask items: two forms each, the key not marked.
        items = [dict(it, typed=False) for it in walked["ask"]["items"]]
    more = _items(topic, step.count * 2, seed, choice=True, withhold=True)
    seen = {it["prompt"] for it in items}
    for it in more:
        if len(items) >= step.count:
            break
        if it["prompt"] in seen or not it.get("choices"):
            continue
        seen.add(it["prompt"])
        items.append(it)
    if len(items) < 3:
        # Too few pairs to choose between: typed items, the form named.
        for it in _items(topic, step.count, seed + 1):
            if len(items) >= step.count:
                break
            if it["prompt"] not in seen:
                seen.add(it["prompt"])
                items.append(it)
    found = lesson(topic, words=db()) or {}
    return {
        "kind": "rule", "topic": topic,
        "notice": session.notice(topic),
        "items": items[:step.count],
        "glosses": _glosses_for([it.get("lemma", "") for it in items]),
        "after": {
            "gist_ru": found.get("gist_ru"),
            "points_ru": (found.get("points_ru") or [])[:3],
            "more": max(0, len(found.get("points_ru") or []) - 3),
            "sources": found.get("sources") or [],
            "rule": found.get("rule"),
            "explain": walked["explain"] if walked else None,
            "contrast": walked["contrast"] if walked else [],
        },
    }


def _practice(inputs, made, step, seed) -> dict:
    """Blocked on the topic, then mixed with the contrasting topic."""
    import random

    topic, detail = made.topic, step.detail
    blocked = _items(topic, detail["blocked"], seed)
    contrast = detail.get("contrast")
    mixed = _items(topic, detail["mixed"], seed + 7)
    if contrast:
        other = _items(contrast, max(1, detail["mixed"] // 2), seed + 11)
        mixed = mixed[:detail["mixed"] - len(other)] + other
        random.Random(seed).shuffle(mixed)
    seen, out = set(), []
    for block, items in (("blocked", blocked), ("mixed", mixed)):
        for it in items:
            if it["prompt"] in seen:
                continue
            seen.add(it["prompt"])
            out.append(it | {"block": block})
    return {"kind": "items", "items": out, "contrast": contrast,
            "glosses": _glosses_for([it.get("lemma", "") for it in out])}


def _words(inputs, made, step, seed) -> dict:
    from .. import session

    lemmas = inputs.words_new or inputs.words
    made_words = session.word_items(db(), tuple(lemmas), step.count, seed)
    return {"kind": "words", "items": [
        {k: v for k, v in w.items() if k != "answer"} | {
            "token": session.sign_word(w), "typed": True, "topic": "sonad"}
        for w in made_words]}


def _material(unit: str, kind: str) -> dict | None:
    from .reports import unit_material

    try:
        found = unit_material(unit)["material"]
    except HTTPException:
        return None
    return next((m for m in found if m["kind"] == kind), None)


def _listening(inputs, made, step, seed) -> dict:
    """The unit's checked dialogue, heard; or heard items (sounds, numbers) at
    the start; or dictation. The transcript is shown after the answers."""
    source = step.detail.get("material")
    if source == "dialoog":
        found = _material(made.unit, "dialoog")
        if found and found["questions"]:
            return {"kind": "material", "material": found,
                    "questions": found["questions"][:step.count]}
    if source == "heli":
        items: list[dict] = []
        for topic in ("arvud", "tahestik"):
            items += [it for it in _items(topic, step.count * 2, seed + len(items))
                      if it.get("say") or it.get("label") == "numbritega"]
        if items:
            return {"kind": "items", "items": items[:step.count]}
    from .speech import dictation_next

    return {"kind": "dictation", **dictation_next(count=step.count, seed=seed)}


def _reading(inputs, made, step, seed) -> dict:
    found = _material(made.unit, "tekst")
    if not found:
        return _listening(inputs, made, step, seed)
    return {"kind": "material", "material": found,
            "questions": found["questions"][:step.count]}


def _speaking(inputs, made, step, seed) -> dict:
    """Sentences to repeat after the recording, then questions to answer."""
    import random

    from ..speaking import bank

    shadow: list[str] = []
    found = _material(made.unit, "dialoog")
    if found:
        shadow = [t["text"] for t in found["turns"] if 3 <= len(t["text"].split()) <= 10]
    if not shadow and made.topic:
        from ..lessons import examples

        try:
            shadow = [r["before"] + r["answer"] + r["after"]
                      for r in examples(made.topic, count=6, seed=seed)]
        except Exception:  # noqa: BLE001 - no frames: the step keeps its task
            shadow = []
    rng = random.Random(seed)
    rng.shuffle(shadow)
    tasks = [q for q in bank() if q.kind == "vestlus"]
    rng.shuffle(tasks)
    return {"kind": "speaking",
            "shadow": shadow[:step.detail.get("shadow", 1)],
            "tasks": [{"question": q.question, "topic": q.topic, "hint_ru": q.hint_ru}
                      for q in tasks[:step.detail.get("tasks", 0)]],
            "level": "B1" if inputs.stage == "B1" else "A2"}


def _writing(inputs, made, step, seed) -> dict:
    """One writing task in HARNO's format (A2's below B1), checked by code first."""
    import random

    from ..writingtasks import BANK, PROMPTS_BY

    level = "B1" if inputs.stage == "B1" else "A2"
    tasks = [t for t in BANK[level] if t.task_no == 1 and t.kind != "kusimustik"]
    task = random.Random(seed).choice(tasks)
    return {"kind": "writing", "task": task.to_dict(), "level": level,
            "prompts_by": PROMPTS_BY}


def _check(inputs, made, step, seed) -> dict:
    """The exit check: items from the unit's topics so far, no hints, counted
    once; in a unit's fifth session the unit check itself."""
    if step.detail.get("unit_check"):
        from .practice import unit_check_items

        found = unit_check_items(made.unit, seed=seed)
        # Graded as a whole from its seed: the page needs no key.
        found["items"] = [{k: v for k, v in it.items() if k not in _KEYS}
                          for it in found["items"]]
        return {"kind": "unit-check", **found}
    from ..curriculum import by_id
    from ..practice import missing_here
    from ..progress import mastered
    from ..units import by_id as unit_by_id

    unit = unit_by_id(made.unit)
    absent = missing_here()
    done = mastered(progress_db())
    topics = [t for t in unit.topics
              if by_id(t).generator and t not in absent and (t == made.topic or t in done)]
    if made.topic and made.topic not in topics:
        topics.insert(0, made.topic)
    items: list[dict] = []
    for n, topic in enumerate(topics or ([made.topic] if made.topic else [])):
        share = step.count - len(items) if n == len(topics) - 1 else max(1, step.count // len(topics))
        items += _items(topic, share, seed + n)
    return {"kind": "items", "items": items[:step.count], "no_hints": True,
            "glosses": _glosses_for([it.get("lemma", "") for it in items])}


_BUILDERS = {"kordamine": _review, "reegel": _rule, "harjutamine": _practice,
             "sonad": _words, "kuulamine": _listening, "lugemine": _reading,
             "raakimine": _speaking, "kirjutamine": _writing, "kontroll": _check}


# --------------------------------------------------------------------------
# Answering
# --------------------------------------------------------------------------

class SessionAnswer(BaseModel):
    #: item | card | word | material | dictation
    kind: str = "item"
    step: str = ""
    token: str = Field(default="", max_length=8000)
    given: str = Field(default="", max_length=800)
    attempt: int = Field(default=1, ge=1, le=2)
    #: The item was offered as a choice: nothing left to retry.
    choice: bool = False
    event_id: str = Field(default="", max_length=80)
    latency_ms: int | None = Field(default=None, ge=0)
    #: A review card: its id, and the learner's rating for a meaning card.
    id: str = ""
    rating: str | None = None
    #: Checked material: which text and which question.
    material: str = ""
    item: str = ""


@router.post("/api/session/answer")
def session_answer(req: SessionAnswer) -> dict:
    """Grade one answer by code. Only the first attempt is recorded."""
    if req.kind == "item":
        return _answer_item(req)
    if req.kind == "card":
        from .review import ReviewGrade, review_grade

        return review_grade(ReviewGrade(id=req.id, event_id=req.event_id,
                                        rating=req.rating,
                                        given=None if req.rating else req.given,
                                        latency_ms=req.latency_ms))
    if req.kind == "word":
        from .. import session

        try:
            return session.answer_word(req.token, req.given, req.attempt)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=_STALE) from exc
    if req.kind == "material":
        from .reports import MaterialAnswer, material_answer

        return material_answer(MaterialAnswer(material=req.material, item=req.item,
                                              answer=req.given))
    if req.kind == "dictation":
        from .speech import DictationAnswer, dictation_answer

        return dictation_answer(DictationAnswer(token=req.token, typed=req.given))
    raise HTTPException(status_code=400, detail=f"unknown answer kind: {req.kind!r}")


_STALE = ("Задание не удалось проверить: оно выдано не этим сервером или устарело. "
          "Открой шаг ещё раз.")


def _answer_item(req: SessionAnswer) -> dict:
    from .. import session
    from ..itemref import verify
    from .practice import AnswerRequest, practice_answer

    try:
        issued = verify(req.token)["item"]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_STALE) from exc
    first = req.attempt == 1
    graded = practice_answer(AnswerRequest(
        topic=issued["topic"], prompt=issued["prompt"], answer=issued["answer"],
        given=req.given, token=req.token, event_id=req.event_id if first else "",
        latency_ms=req.latency_ms, record=first))
    retry = (first and not graded["correct"] and req.step in session.RETRY_STEPS
             and not req.choice)
    if retry:
        # The key stays on the server: a hint from code, and one more try.
        return {"correct": False, "retry": True, "event_id": graded.get("event_id"),
                "hint_ru": session.hint(issued, req.given)}
    return graded | {"retry": False, "solution": _solution(issued, req.given, graded)}


def _solution(issued: dict, given: str, graded: dict) -> str:
    """The sentence completed: with the learner's form when it was right."""
    from ..item import fill

    key = issued["answer"].split(" ~ ")[0]
    form = given.strip() if graded["correct"] and given.strip() else key
    return fill(issued["prompt"], form) if "____" in issued["prompt"] else issued["answer"]


class StepDone(BaseModel):
    session: str = Field(max_length=80)
    asked: int = Field(default=0, ge=0, le=200)
    correct: int = Field(default=0, ge=0, le=200)
    skipped: int = Field(default=0, ge=0, le=200)


@router.post("/api/session/step/{step}/done")
def session_step_done(step: str, req: StepDone) -> dict:
    """A step is done; after the last, the session is (ADR-0009)."""
    from .. import session

    try:
        return session.finish_step(req.session, step, asked=req.asked,
                                   correct=req.correct, skipped=req.skipped)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --------------------------------------------------------------------------
# Onboarding: the goal, sessions a week, and the placement check
# --------------------------------------------------------------------------

class GoalIn(BaseModel):
    goal: str
    per_week: int | None = Field(default=None, ge=1, le=7)


@router.get("/api/session/goal")
def read_learning_goal() -> dict:
    from .. import evidence, session

    with evidence.connect() as log:
        return {"goal": session.goal(log), "goals": [
            {"id": g, "et": et, "ru": ru} for g, (et, ru) in session.GOAL_NAMES.items()]}


@router.post("/api/session/goal")
def set_learning_goal(req: GoalIn) -> dict:
    from .. import session

    try:
        session.set_goal(req.goal, req.per_week)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return read_learning_goal()


class Placed(BaseModel):
    unit: str
    token: str = Field(max_length=8000)
    given: str = Field(default="", max_length=400)


class PlacementIn(BaseModel):
    answers: list[Placed] = Field(default_factory=list, max_length=12)
    #: Record the result and move navigation past the units before it.
    apply: bool = False


@router.post("/api/session/placement")
def placement(req: PlacementIn) -> dict:
    """The adaptive check: at most twelve items, three a unit, graded here by
    code from their tokens, placing by unit. Nothing is mastered by it; applied,
    it moves past the units before the start, which can be undone in Kursus."""
    from .. import session
    from ..itemref import verify
    from ..item import accepts

    results, rows = [], []
    for a in req.answers:
        try:
            issued = verify(a.token)["item"]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=_STALE) from exc
        ok = accepts(issued["answer"], a.given)
        results.append((a.unit, ok))
        rows.append({"unit": a.unit, "topic": issued["topic"], "prompt": issued["prompt"],
                     "given": a.given, "expected": issued["answer"], "correct": ok})
    placed = session.place(results)
    if not placed["done"]:
        from ..units import by_id

        seed = session.seed_of("placement", len(results), placed["unit"])
        items: list[dict] = []
        topics = session.probe_topics(placed["unit"])
        for n, topic in enumerate(topics):
            # A generator can give fewer than asked: the unit's next core topic
            # fills the rest, so every probe asks its three.
            items += _items(topic, placed["left"] + 3, seed + n)
            if len(items) >= placed["left"]:
                break
        if not items:
            raise HTTPException(status_code=400, detail=(
                "Для этого блока сейчас нет заданий: проверку можно закончить здесь."))
        return placed | {"topic": topics[0], "et": by_id(placed["unit"]).et,
                         "items": items[:placed["left"]]}
    from ..units import by_id

    start = by_id(placed["start"])
    out = placed | {"start_et": start.et, "start_n": start.n, "review": rows}
    if req.apply:
        from ..course import set_units_skip

        session.record_placement(rows, start.id)
        if placed["skip"]:
            set_units_skip(progress_db(), placed["skip"], True)
    return out


# --------------------------------------------------------------------------
# Writing and speaking: code's checklist, then the model's comments
# --------------------------------------------------------------------------

class WritingIn(BaseModel):
    task: str = Field(max_length=80)
    text: str = Field(default="", max_length=6000)


@router.post("/api/session/writing")
def session_writing(req: WritingIn) -> dict:
    """Code's checklist for a written task (`writingtasks.check`), recorded as
    writing practice. Never a mark."""
    from .. import evidence
    from ..writingtasks import by_id, check

    try:
        task = by_id(req.task)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Такого задания нет.") from exc
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Сначала напиши текст.")
    result = check(task, req.text)
    evidence.record("writing", {"task": task.id, "words": result["words"],
                                "long_enough": result["long_enough"],
                                "errors": result["errors"], "source": "session"})
    return result


class FeedbackIn(BaseModel):
    kind: str
    text: str = Field(max_length=6000)
    level: str = "A2"
    task: str = Field(default="", max_length=600)
    lang: str = "ru"


@router.post("/api/session/feedback")
def session_feedback(req: FeedbackIn) -> dict:
    """The model's comments against HARNO's descriptors: labelled, quoting the
    learner's text, never a score (`tutor.descriptor_feedback`)."""
    from .. import tutor

    try:
        return tutor.descriptor_feedback(req.kind, req.text, level=req.level,
                                         task=req.task, lang=req.lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class MiksIn(BaseModel):
    event_id: str = Field(max_length=80)
    lang: str = "ru"


@router.post("/api/session/miks")
def session_miks(req: MiksIn) -> dict:
    """*Miks?* after a miss: the model explains the recorded attempt in the
    explanation language from the item's EKK section, and decides nothing."""
    from .. import tutor

    try:
        return tutor.explain_attempt(req.event_id, req.lang).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Такой попытки нет.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class AskIn(BaseModel):
    question: str = Field(max_length=600)
    lang: str = "ru"


@router.post("/api/rule/{topic}/ask")
def rule_ask(topic: str, req: AskIn) -> dict:
    """The rule page's question box: answered by the model from the topic's
    sources alone, labelled, never a verdict on anything the learner wrote."""
    from .. import tutor

    try:
        return tutor.ask_rule(topic, req.question, req.lang).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Такой темы нет.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
