"""The session and the next task (ADR-0009): what today holds, built by code.

`compose()` is a pure function of `Inputs`, like `planning.plan`: the same
evidence on the same day gives the same session, so it can be tested with
fixtures and explained line by line. `gather()` reads the evidence; nothing
here asks a model.

**The seven steps**, grouped under the session line's three phases:

| Phase | Step | What |
|---|---|---|
| Õpi | Kordamine | due cards and yesterday's misses, at most `REVIEW_CAP` (5 minutes) |
| Õpi | Reegel | 6–10 items chosen between two forms, then the rule (EKK) |
| Harjuta | Harjutamine | blocked, then mixed with the contrasting topic; one retry with a hint |
| Harjuta | Sõnad | the unit's words in EKI's phrases; a word enters review on its first correct recall |
| Harjuta | Kuulamine | the unit's checked dialogue, or dictation; transcript after |
| Harjuta | Rääkimine | shadowing, then a short task; the model's feedback is labelled |
| Kontrolli | Kontroll | 3–5 items, no hints, counted once; the unit check in a unit's fifth session |

**The rotation.** Across a unit's five sessions the emphasis moves: the rule →
words and listening → a speaking task → reading and writing → the unit check.
The emphasis sizes the steps; in the fourth session Lugemine and Kirjutamine
take the places of Kuulamine and Rääkimine where the unit has a checked text
and a writing task fits its stage.

**The next task** (`next_task`): review first when the due queue is long;
remediation after a failed unit check; otherwise today's session, and once it
is done the skill practised least recently; with a sitting chosen and near, an
exam-format task, which leads once the session is done in the last two weeks.
Täna shows one *Jätka* and two alternatives, each with its reason from here.

**Grading stays where it is.** Items are the generators' own, signed as
practice is (`eesti/itemref.py`), and graded by `api.practice`; only the first
attempt is recorded, so a retry after a hint is graded and never counted
(`api/session.py`). Words are signed apart (`sign_word`), so a word token can
never be graded as a drill.

The session's own events say what was started and finished; they change no
projection (`LOG_ONLY` below): mastery, review and readiness follow the
attempts, cards and answers the steps record.
"""

from __future__ import annotations

import hashlib
import math
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone

from . import evidence

# --------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------

#: The steps in session order. `lugemine` and `kirjutamine` stand in for
#: `kuulamine` and `raakimine` in a reading-and-writing session.
STEPS = ("kordamine", "reegel", "harjutamine", "sonad", "kuulamine", "raakimine", "kontroll")

#: Each step's Estonian name and its gloss.
NAMES = {
    "kordamine": ("Kordamine", "повторение"),
    "reegel": ("Reegel", "правило на практике"),
    "harjutamine": ("Harjutamine", "упражнения"),
    "sonad": ("Sõnad", "слова"),
    "kuulamine": ("Kuulamine", "аудирование"),
    "lugemine": ("Lugemine", "чтение"),
    "raakimine": ("Rääkimine", "говорение"),
    "kirjutamine": ("Kirjutamine", "письмо"),
    "kontroll": ("Kontroll", "проверка"),
}

#: The session line's three phases (the app's learn → practise → check).
PHASES = (("opi", "Õpi", "разбери"), ("harjuta", "Harjuta", "попробуй"),
          ("kontrolli", "Kontrolli", "проверь"))
PHASE_OF = {"kordamine": "opi", "reegel": "opi", "harjutamine": "harjuta",
            "sonad": "harjuta", "kuulamine": "harjuta", "lugemine": "harjuta",
            "raakimine": "harjuta", "kirjutamine": "harjuta", "kontroll": "kontrolli"}

#: The emphasis of a unit's sessions 1–5, in order (ADR-0009).
ROTATION = (
    ("reeglid", "Reegel", "правило"),
    ("sonad", "Sõnad ja kuulamine", "слова и аудирование"),
    ("raakimine", "Rääkimine", "говорение"),
    ("kirjutamine", "Lugemine ja kirjutamine", "чтение и письмо"),
    ("kontroll", "Ühiku kontroll", "проверка блока"),
)
SESSIONS_PER_UNIT = len(ROTATION)

#: Steps a first miss is retried in, with a hint (DESIGN.md, Practice rhythm).
#: Review and the exit check count once with no hint; a choice between two
#: forms has nothing left to retry.
RETRY_STEPS = frozenset({"harjutamine", "sonad"})

# --------------------------------------------------------------------------
# Sizes and minutes
# --------------------------------------------------------------------------

#: The review step's cap: at most five minutes at half a minute a card.
REVIEW_CAP = 10
#: A queue this long makes review the next task on its own (capped there too).
LONG_QUEUE = 30
#: The exit check's size (3–5 in ADR-0009).
CHECK_ITEMS = 4

#: Items per step for each emphasis. `blocked` and `mixed` split Harjutamine.
SIZES = {
    "reeglid": {"reegel": 8, "blocked": 5, "mixed": 5, "sonad": 4, "kuulamine": 3,
                "shadow": 2, "tasks": 1},
    "sonad": {"reegel": 6, "blocked": 3, "mixed": 4, "sonad": 8, "kuulamine": 5,
              "shadow": 2, "tasks": 1},
    "raakimine": {"reegel": 6, "blocked": 3, "mixed": 4, "sonad": 4, "kuulamine": 3,
                  "shadow": 3, "tasks": 2},
    "kirjutamine": {"reegel": 6, "blocked": 2, "mixed": 3, "sonad": 3, "kuulamine": 3,
                    "lugemine": 5, "shadow": 2, "tasks": 1},
    "kontroll": {"reegel": 6, "blocked": 3, "mixed": 4, "sonad": 4, "kuulamine": 3,
                 "shadow": 2, "tasks": 1},
}

#: Estimated minutes per item, by step: what the plan's minutes are made of.
MINUTES_PER = {"kordamine": 0.5, "reegel": 0.75, "harjutamine": 0.75, "sonad": 0.5,
               "kuulamine": 1.0, "lugemine": 1.0, "raakimine": 1.0, "kirjutamine": 10.0,
               "kontroll": 0.5}
#: A speaking task (an answer, its transcript and the feedback) against one
#: sentence repeated after the recording.
TASK_MINUTES = 3

#: Days to a chosen sitting from which exam-format tasks join, and lead.
EXAM_NEAR = 60
EXAM_LEADS = 14

#: Explanation languages, each with what choosing it means today, said in it:
#: the app's own explanations are Russian until the catalogue has the others
#: (S4); a model's explanations already answer in the chosen language.
LANGUAGES = (
    ("ru", "Русский", "Объяснения, подсказки и комментарии модели — на русском."),
    ("uk", "Українська", "Пояснення застосунку поки що російською: український текст ще "
     "готується. Пояснення моделі (Miks?) — українською. Змінити мову можна в профілі."),
    ("en", "English", "The app's own explanations are in Russian for now: the English text "
     "is being prepared. The model's explanations (Miks?) answer in English. You can "
     "change the language in Profile."),
)

#: Goals the onboarding offers (ADR-0009), and the lane each leads to first.
GOALS = {"igapaev": "path", "too": "path", "a2": "exam", "b1": "exam"}
GOAL_NAMES = {"igapaev": ("Igapäevaelu", "для жизни"), "too": ("Töö", "для работы"),
              "a2": ("A2 eksam", "экзамен A2"), "b1": ("B1 eksam", "экзамен B1")}

#: Session events. They record what was started and finished and change no
#: projection: mastery and review follow the attempts and cards themselves.
STARTED, STEP_DONE, DONE = "session-started", "session-step-done", "session-done"
GOAL_SET, PLACED, WORD = "learning-goal-set", "placement-checked", "word-recalled"
LOG_ONLY = (STARTED, STEP_DONE, DONE, GOAL_SET, PLACED, WORD)
for _type in LOG_ONLY:
    evidence.applies(_type)(lambda stores, ev: None)


def _count(n: int, one: str, few: str, many: str) -> str:
    tail = n % 100
    if 11 <= tail <= 14:
        return f"{n} {many}"
    return f"{n} {one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many}"


def local_day(now: datetime | None = None) -> date:
    """The learner's day: Tallinn's, as reminders and the rhythm count it."""
    from zoneinfo import ZoneInfo

    from .reminders import ZONE

    return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(ZONE)).date()


def day_start(day: date) -> str:
    """Midnight of a local day, as an ISO time in UTC (for `evidence.since`)."""
    from zoneinfo import ZoneInfo

    from .reminders import ZONE

    start = datetime.combine(day, datetime.min.time(), tzinfo=ZoneInfo(ZONE))
    return start.astimezone(timezone.utc).isoformat()


def seed_of(*parts: object) -> int:
    """A stable seed: the same session regenerates the same items."""
    text = ":".join(str(p) for p in parts)
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) % 2**31


# --------------------------------------------------------------------------
# The evidence a session is made from
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Inputs:
    today: str
    unit: str
    #: The topic the rule and practice steps teach; None once every open topic
    #: is mastered (the session then reviews and checks).
    topic: str | None
    #: The session's place in the unit's five (1–5).
    n: int = 1
    due: int = 0
    #: Cards made from yesterday's misses that are not due yet.
    yesterday: int = 0
    #: Unit words with no review card yet, and all the unit's words.
    words_new: tuple[str, ...] = ()
    words: tuple[str, ...] = ()
    walk: bool = False
    drillable: bool = True
    #: The topic practised beside this one in the mixed half (`contrast_of`).
    contrast: str | None = None
    #: The unit's checked material: `dialoog`, `tekst`.
    material: tuple[str, ...] = ()
    #: Steps already done in today's session.
    done: tuple[str, ...] = ()
    started: bool = False
    #: Sessions finished in this unit before today's.
    sessions_done: int = 0
    #: The unit's last check: passed, and the topics of the parts it failed.
    check_failed: tuple[str, ...] = ()
    #: Days since each exam part was last practised (None: never).
    skills: dict = field(default_factory=dict)
    sitting_days: int | None = None
    exam_level: str | None = None
    goal: str | None = None
    #: The weakest rule: (topic, its name, accuracy) or None.
    weak: tuple[str, str, float | None] | None = None
    stage: str = "A1"
    writing: bool = False
    #: Items in the unit's check (`unitcheck.parts` × five).
    check_size: int = 0
    #: A session on `topic` alone: its rule, practice and check.
    focus: bool = False

    def digest(self) -> str:
        import json

        body = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(body.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Step:
    id: str
    et: str
    ru: str
    phase: str
    count: int
    minutes: int
    why_ru: str
    state: str = "todo"         # done | current | todo
    #: Sizes a builder reads (`blocked`, `mixed`, `shadow`, `tasks`, `unit_check`).
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Session:
    id: str
    today: str
    unit: str
    topic: str | None
    n: int
    emphasis: str
    steps: tuple[Step, ...]
    seed: int
    inputs: str
    kind: str = "today"         # today | topic

    @property
    def minutes(self) -> int:
        return sum(s.minutes for s in self.steps)

    @property
    def done(self) -> bool:
        return bool(self.steps) and all(s.state == "done" for s in self.steps)

    def step(self, step_id: str) -> Step | None:
        return next((s for s in self.steps if s.id == step_id), None)

    def to_dict(self) -> dict:
        from .units import by_id

        unit = by_id(self.unit)
        emphasis = next(r for r in ROTATION if r[0] == self.emphasis)
        topic = None
        if self.topic:
            from .curriculum import by_id as topic_by_id

            t = topic_by_id(self.topic)
            topic = {"id": t.id, "et": t.et, "ru": t.ru}
        return {
            "id": self.id, "kind": self.kind, "today": self.today, "n": self.n,
            "of": SESSIONS_PER_UNIT,
            "unit": {"id": unit.id, "n": unit.n, "et": unit.et, "stage": unit.stage,
                     "goal_ru": unit.goal_ru},
            "topic": topic,
            "emphasis": {"id": emphasis[0], "et": emphasis[1], "ru": emphasis[2]},
            "minutes": self.minutes, "seed": self.seed, "done": self.done,
            "inputs": self.inputs,
            "phases": [{"id": p, "et": et, "ru": ru} for p, et, ru in PHASES],
            "steps": [asdict(s) for s in self.steps],
        }


def _minutes(step: str, count: int) -> int:
    return max(1, math.ceil(count * MINUTES_PER[step]))


def compose(inputs: Inputs) -> Session:
    """Today's session from the evidence: its steps, sizes, reasons and states."""
    emphasis = ROTATION[(inputs.n - 1) % SESSIONS_PER_UNIT][0]
    size = SIZES[emphasis]
    steps: list[Step] = []

    def add(step_id: str, count: int, why: str, **detail) -> None:
        et, ru = NAMES[step_id]
        minutes = _minutes(step_id, count)
        if step_id == "raakimine":
            minutes = detail["shadow"] + TASK_MINUTES * detail["tasks"]
        steps.append(Step(step_id, et, ru, PHASE_OF[step_id], count, minutes, why,
                          detail=detail))

    review = 0 if inputs.focus else min(REVIEW_CAP, inputs.due + inputs.yesterday)
    if review:
        parts = []
        if inputs.due:
            parts.append(f"к повторению {_count(inputs.due, 'карточка', 'карточки', 'карточек')}")
        if inputs.yesterday:
            parts.append(f"вчерашних ошибок {inputs.yesterday}")
        add("kordamine", review, "Сначала то, что пора вспомнить: " + ", ".join(parts)
            + f". Не больше {REVIEW_CAP} карточек, около пяти минут.")

    teaching = inputs.topic is not None and inputs.drillable
    if teaching:
        add("reegel", size["reegel"],
            "Сначала выбираешь форму сам, потом читаешь правило по EKK.")
        blocked, mixed = size["blocked"], size["mixed"]
        mixed_why = (" Потом вперемешку с соседней темой, чтобы их различать."
                     if inputs.contrast else " Потом вперемешку с другими правилами темы.")
        add("harjutamine", blocked + mixed,
            "Сначала задания на одно правило." + mixed_why
            + " Ошибка — подсказка и вторая попытка; считается только первая.",
            blocked=blocked, mixed=mixed, contrast=inputs.contrast)

    words = () if inputs.focus else inputs.words_new or inputs.words
    if words:
        n = min(size["sonad"], len(words))
        add("sonad", n, "Слова блока во фразах EKI. Слово уходит в повторение, "
            "когда ты впервые вспомнил его верно." if inputs.words_new else
            "Слова блока во фразах EKI: все они уже в повторении, это закрепление.")

    reading = emphasis == "kirjutamine" and "tekst" in inputs.material
    if inputs.focus:
        pass
    elif reading:
        add("lugemine", size["lugemine"], "Текст блока и вопросы к нему; ответы "
            "проверяет код по самому тексту.", material="tekst")
    else:
        heard = "dialoog" if "dialoog" in inputs.material else (
            "heli" if inputs.stage == "algus" else "dikteerimine")
        why = {"dialoog": "Диалог блока на слух, вопросы к нему; текст — после ответов.",
               "heli": "Звуки и числа на слух, записи EKI.",
               "dikteerimine": "Предложения на слух: запиши услышанное, текст — после."}[heard]
        add("kuulamine", size["kuulamine"], why, material=heard)

    writing = emphasis == "kirjutamine" and inputs.writing
    if inputs.focus:
        pass
    elif writing:
        add("kirjutamine", 1, "Короткий текст в формате экзамена HARNO: сначала "
            "проверка кодом, потом комментарий модели — без оценки.")
    else:
        tasks = 0 if inputs.stage == "algus" else size["tasks"]
        add("raakimine", size["shadow"] + tasks,
            "Повтори за записью, потом ответь сам. Ты подтверждаешь распознанный "
            "текст; комментарий модели — после ответа, без оценки."
            if tasks else "Повтори за записью вслух: слух и произношение вместе.",
            shadow=size["shadow"], tasks=tasks)

    if emphasis == "kontroll" and inputs.check_size and not inputs.focus:
        add("kontroll", inputs.check_size, "Пятое занятие блока — проверка блока: по "
            "пять заданий на тему, нужно не меньше четырёх из пяти.", unit_check=True)
    elif teaching or (inputs.words and not inputs.focus):
        add("kontroll", CHECK_ITEMS, "Короткая проверка без подсказок: считается "
            "один раз.", unit_check=False)

    current = next((s.id for s in steps if s.id not in inputs.done), None)
    steps = [Step(s.id, s.et, s.ru, s.phase, s.count, s.minutes, s.why_ru,
                  "done" if s.id in inputs.done else "current" if s.id == current else "todo",
                  s.detail) for s in steps]
    sid = session_id(inputs)
    return Session(sid, inputs.today, inputs.unit, inputs.topic, inputs.n, emphasis,
                   tuple(steps), seed_of(sid, inputs.topic), inputs.digest(),
                   "topic" if inputs.focus else "today")


def session_id(inputs: Inputs) -> str:
    """`<day>:<unit>:<n>` for the day's session, `<day>:<unit>:<topic>` for a
    session on one topic."""
    third = inputs.topic if inputs.focus else inputs.n
    return f"{inputs.today}:{inputs.unit}:{third}"


# --------------------------------------------------------------------------
# The next task: one Jätka and two alternatives, each with its reason
# --------------------------------------------------------------------------

#: Exam parts: where each is practised, and its names.
SKILLS = {
    "kuulamine": ("#listen", "Kuulamine", "аудирование"),
    "lugemine": ("#read", "Lugemine", "чтение"),
    "raakimine": ("#speak", "Rääkimine", "говорение"),
    "kirjutamine": ("#write", "Kirjutamine", "письмо"),
}


def _task(kind: str, et: str, ru: str, why: str, href: str, minutes: int | None = None) -> dict:
    return {"kind": kind, "et": et, "ru": ru, "why_ru": why, "href": href,
            "minutes": minutes}


def _least_practised(skills: dict) -> list[str]:
    """Exam parts, practised least recently first; never practised comes first,
    and ties go to the exam's own order."""
    order = list(SKILLS)
    return sorted(order, key=lambda p: (skills.get(p) is not None, -(skills.get(p) or 0),
                                        order.index(p)))


def _skill_task(part: str, days: int | None) -> dict:
    href, et, ru = SKILLS[part]
    # The link names the part; its reason says only why.
    why = ("Ещё не было ни одного занятия." if days is None
           else f"{_count(days, 'день', 'дня', 'дней').capitalize()} без практики."
           if days else "Меньше всего практики за последнее время.")
    return _task("skill", et, ru, why, href)


def next_task(inputs: Inputs, session: Session) -> dict:
    """The primary task and two alternatives, decided by code, with reasons."""
    from .units import by_id as unit_by_id

    candidates: list[dict] = []
    primary: dict | None = None

    review = _task("review", "Kordamine", "повторение",
                   f"Ждут {_count(inputs.due, 'карточка', 'карточки', 'карточек')}: "
                   "повторить вовремя проще, чем учить заново.", "#review",
                   max(1, math.ceil(min(inputs.due, 20) * MINUTES_PER["kordamine"])))
    if inputs.due >= LONG_QUEUE:
        review["why_ru"] = (f"Очередь длинная: {_count(inputs.due, 'карточка', 'карточки', 'карточек')}. "
                            "Сначала повторение, до 20 карточек.")
        primary = review
    elif inputs.due:
        candidates.append(review)

    if inputs.check_failed:
        from .curriculum import by_id as topic_by_id

        failed = topic_by_id(inputs.check_failed[0])
        remedy = _task("remedy", failed.et, "новые задания",
                       f"Проверка блока «{unit_by_id(inputs.unit).et}» не сдана по этой "
                       "теме: новые задания на неё, потом проверку можно повторить.",
                       f"#session/{failed.id}", 8)
        if primary is None:
            primary = remedy
        else:
            candidates.insert(0, remedy)

    today = _task("session", "Tänane tund", "занятие на сегодня",
                  f"Блок {unit_by_id(inputs.unit).n}, занятие {inputs.n} из "
                  f"{SESSIONS_PER_UNIT}: {ROTATION[(inputs.n - 1) % SESSIONS_PER_UNIT][2]}.",
                  "#session", session.minutes)
    exam = None
    if inputs.sitting_days is not None and 0 <= inputs.sitting_days <= EXAM_NEAR \
            and inputs.exam_level:
        exam = _task("exam", f"Proovieksam {inputs.exam_level}", "пробный экзамен",
                     f"До экзамена {_count(inputs.sitting_days, 'день', 'дня', 'дней')}: "
                     "задания в формате HARNO, на время.", "#exam")

    if not session.done:
        if primary is None:
            primary = today
        else:
            candidates.insert(0, today)
    elif primary is None:
        if exam and inputs.sitting_days <= EXAM_LEADS:
            primary, exam = exam, None
        else:
            part = _least_practised(inputs.skills)[0]
            primary = _skill_task(part, inputs.skills.get(part))

    if exam:
        candidates.insert(0 if session.done else 1, exam)
    parts = [p for p in _least_practised(inputs.skills) if SKILLS[p][0] != primary["href"]]
    candidates.append(_skill_task(parts[0], inputs.skills.get(parts[0])))
    if inputs.weak:
        topic, name, accuracy = inputs.weak
        pct = f"точность {round(accuracy * 100)}%" if accuracy is not None else "карточки забываются"
        candidates.append(_task("weak", name, "слабое место",
                                f"{pct.capitalize()}: стоит повторить правило.", f"#session/{topic}", 5))
    # A second part when nothing else has a reason: two alternatives always.
    candidates.append(_skill_task(parts[1], inputs.skills.get(parts[1])))
    seen = {primary["href"]}
    alternatives = []
    for c in candidates:
        if c["href"] in seen:
            continue
        seen.add(c["href"])
        alternatives.append(c)
        if len(alternatives) == 2:
            break
    return {"primary": primary, "alternatives": alternatives}


# --------------------------------------------------------------------------
# Reading the evidence
# --------------------------------------------------------------------------

def contrast_of(topic: str) -> str | None:
    """The topic mixed in after the blocked half: the previous drillable topic of
    the same unit, else the topic's last drillable prerequisite. None when there
    is neither: the mixed half is then the topic's own rules, mixed."""
    from .curriculum import by_id
    from .practice import missing_here
    from .units import home

    absent = missing_here()

    def drillable(t: str) -> bool:
        return by_id(t).generator is not None and t not in absent

    unit = home(topic)
    before = unit.topics[:unit.topics.index(topic)]
    for t in reversed(before):
        if drillable(t):
            return t
    for t in reversed(by_id(topic).requires):
        if drillable(t):
            return t
    return None


def _latest(log: sqlite3.Connection, type_: str):
    row = log.execute("SELECT * FROM events WHERE type = ? ORDER BY seq DESC LIMIT 1",
                      (type_,)).fetchone()
    return evidence._row(row) if row else None


def started_today(log: sqlite3.Connection, today: date) -> dict | None:
    """Today's session as it was started, so its unit, place and items hold all
    day even when the path moves on under it."""
    found = [e for e in evidence.since(log, (STARTED,), day_start(today))
             if e.payload.get("today") == today.isoformat()]
    return found[0].payload if found else None


def steps_done(log: sqlite3.Connection, session_id: str, today: date) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        e.payload["step"] for e in evidence.since(log, (STEP_DONE,), day_start(today))
        if e.payload.get("session") == session_id))


def sessions_done(log: sqlite3.Connection, unit: str, before: date) -> int:
    """Sessions of `unit` finished on days before `before`."""
    days = {e.payload.get("today") for e in evidence.since(log, (DONE,), "")
            if e.payload.get("unit") == unit and e.payload.get("today", "") < before.isoformat()}
    return len(days)


def goal(log: sqlite3.Connection) -> dict | None:
    """The learner's goal and sessions a week, from onboarding (`set_goal`)."""
    ev = _latest(log, GOAL_SET)
    return dict(ev.payload) if ev else None


def set_goal(goal_id: str, per_week: int | None = None) -> evidence.Event:
    if goal_id not in GOALS:
        raise ValueError("Выбери одну из целей.")
    if per_week is not None and not 1 <= per_week <= 7:
        raise ValueError("Занятий в неделю — от одного до семи.")
    return evidence.record(GOAL_SET, {"goal": goal_id, "per_week": per_week})


def _skills(log: sqlite3.Connection, now: datetime) -> dict:
    """Days since each exam part was last practised, from the log."""
    from .learner import EXPOSURE_SKILL, SKILL_EVENTS, _when

    last: dict[str, datetime] = {}
    for part, types in SKILL_EVENTS.items():
        row = log.execute(
            f"SELECT ts FROM events WHERE type IN ({','.join('?' * len(types))}) "  # noqa: S608
            "ORDER BY seq DESC LIMIT 1", types).fetchone()
        if row:
            last[part] = _when(row["ts"])
    for row in log.execute("SELECT ts, payload FROM events WHERE type = 'exposure' "
                           "ORDER BY seq DESC LIMIT 200"):
        import json

        part = EXPOSURE_SKILL.get(json.loads(row["payload"]).get("skill") or "", "lugemine")
        when = _when(row["ts"])
        if part not in last or when > last[part]:
            last[part] = when
    # Practice inside a session counts for its part too.
    for row in log.execute("SELECT ts, payload FROM events WHERE type = ? "
                           "ORDER BY seq DESC LIMIT 200", (STEP_DONE,)):
        import json

        part = {"kuulamine": "kuulamine", "lugemine": "lugemine", "raakimine": "raakimine",
                "kirjutamine": "kirjutamine"}.get(json.loads(row["payload"]).get("step"))
        when = _when(row["ts"])
        if part and (part not in last or when > last[part]):
            last[part] = when
    return {p: (max(0, (now - last[p]).days) if p in last else None) for p in SKILLS}


def _yesterday(log: sqlite3.Connection, review: sqlite3.Connection, today: date,
               now: datetime) -> tuple[str, ...]:
    """Cards made from yesterday's misses that are not due yet."""
    keys = []
    for e in evidence.since(log, ("card-added",), day_start(today - timedelta(days=1))):
        if e.ts >= day_start(today) or e.payload.get("source") not in ("drill", None):
            continue
        from .review import item_id

        keys.append(item_id(e.payload["kind"], e.payload["lemma"], e.payload.get("tag")))
    if not keys:
        return ()
    marks = ",".join("?" * len(keys))
    rows = review.execute(f"SELECT id FROM review_items WHERE id IN ({marks}) AND due > ?",  # noqa: S608
                          (*keys, now.isoformat())).fetchall()
    return tuple(r[0] for r in rows)


def _material(unit: str) -> tuple[str, ...]:
    try:
        from contextlib import closing

        from .material import store

        with closing(store.connect()) as conn:
            return tuple(dict.fromkeys(m.kind for m in store.for_unit(conn, unit)))
    except Exception:  # noqa: BLE001 - no material database is no material
        return ()


def _vocab_cards(review: sqlite3.Connection, lemmas: tuple[str, ...]) -> set[str]:
    from .review import item_id

    if not lemmas:
        return set()
    keys = {item_id("vocab", w, "meaning"): w for w in lemmas}
    marks = ",".join("?" * len(keys))
    rows = review.execute(f"SELECT id FROM review_items WHERE id IN ({marks})",  # noqa: S608
                          tuple(keys)).fetchall()
    return {keys[r[0]] for r in rows}


def current_unit(progress: sqlite3.Connection) -> tuple[str, str | None]:
    """The unit and topic the path is on: the resume topic's home, else the last
    unit that is not complete, else the last unit."""
    from .progress import resume
    from .units import UNITS, home

    topic = resume(progress)
    if topic:
        return home(topic).id, topic
    from .unitcheck import passed_units

    passed = passed_units(progress)
    open_ = [u for u in UNITS if u.id not in passed]
    return (open_[0] if open_ else UNITS[-1]).id, None


def gather(now: datetime | None = None, *, topic: str | None = None) -> Inputs:
    """The evidence today's session is made from. With `topic`, a session on that
    topic alone (Kursus' *Õpi*, a remediation, the rule page's *Harjuta*)."""
    from . import config, exam, learner, progress, review, units
    from .curriculum import by_id as topic_by_id
    from .lessontext import WALKS
    from .practice import missing_here

    now = now or datetime.now(timezone.utc)
    today = local_day(now)
    prog = progress.connect(config.learner_db("PROGRESS_DB"))
    rev = review.connect(config.learner_db("REVIEW_DB"))
    with evidence.connect() as log:
        started = None if topic else started_today(log, today)
        if started:
            unit_id, topic_id, n = started["unit"], started["topic"], started["n"]
        elif topic:
            unit_id, topic_id = units.home(topic).id, topic
            n = 1
        else:
            unit_id, topic_id = current_unit(prog)
            n = sessions_done(log, unit_id, today) % SESSIONS_PER_UNIT + 1
        sid = f"{today.isoformat()}:{unit_id}:{topic or n}"
        done = steps_done(log, sid, today)
        skills = _skills(log, now)
        chosen_goal = goal(log)
        yesterday = _yesterday(log, rev, today, now)
        weak = None
        for e in learner.weak_rules(learner.rule_evidence(prog, rev, now))[:1]:
            weak = (e.topic, topic_by_id(e.topic).et, e.accuracy)
        checks = [e for e in evidence.since(log, ("unit-checked",), "")
                  if e.payload.get("unit") == unit_id]
    failed: tuple[str, ...] = ()
    if checks and not all(p.get("passed", p.get("correct", 0) >= 4)
                          for p in checks[-1].payload.get("parts", [])):
        failed = tuple(p["topic"] for p in checks[-1].payload["parts"]
                       if not p.get("passed") and not p["topic"].startswith("checkpoint:"))
    unit = units.by_id(unit_id)
    words = units.words_for(unit)
    have = _vocab_cards(rev, words)
    sitting = exam.goal(prog)
    days = (sitting.sitting - today).days if sitting and sitting.sitting else None
    drillable = bool(topic_id) and topic_by_id(topic_id).generator is not None \
        and topic_id not in missing_here()
    from .unitcheck import PER_PART, parts
    from .writingtasks import BANK

    return Inputs(
        today=today.isoformat(), unit=unit_id, topic=topic_id, n=n,
        due=review.due_count(rev, now), yesterday=len(yesterday),
        words_new=tuple(w for w in words if w not in have), words=tuple(words),
        walk=bool(topic_id) and topic_id in WALKS, drillable=drillable,
        contrast=contrast_of(topic_id) if drillable else None,
        material=_material(unit_id), done=done, started=bool(started),
        sessions_done=n - 1, check_failed=failed, skills=skills,
        sitting_days=days, exam_level=sitting.level if sitting else None,
        goal=(chosen_goal or {}).get("goal"), weak=weak, stage=unit.stage,
        writing=unit.stage != "algus" and bool(BANK.get("B1" if unit.stage == "B1" else "A2")),
        check_size=len(parts(unit)) * PER_PART, focus=bool(topic),
    )


def today(now: datetime | None = None) -> dict:
    """Täna: today's session, the next task, and what the hero shows."""
    inputs = gather(now)
    session = compose(inputs)
    with evidence.connect() as log:
        finished = len({e.payload.get("session") for e in evidence.since(log, (DONE,), "")})
    return {
        "today": inputs.today,
        "session": session.to_dict(),
        "started": inputs.started,
        "next": next_task(inputs, session),
        "hero": hero(session),
        "first": not finished,
        #: Sessions finished so far: after the first, onboarding's last questions.
        "sessions_done": finished,
        "goal": inputs.goal,
        "sitting_days": inputs.sitting_days,
    }


def hero(session: Session) -> dict:
    """What Täna leads with: the rule step's first sentences to notice, the forms
    underlined and not named, or the unit's title and goal."""
    from .units import by_id

    unit = by_id(session.unit)
    plain = {"kind": "unit", "et": unit.et, "n": unit.n, "goal_ru": unit.goal_ru}
    if not session.topic or session.step("reegel") is None \
            or session.step("reegel").state == "done":
        return plain
    try:
        found = notice(session.topic)
    except Exception:  # noqa: BLE001 - a hero is never worth failing Täna
        found = None
    if not found:
        return plain
    return {"kind": "notice", "examples": found["examples"][:2],
            "question_ru": found["question_ru"], "topic": session.topic}


def notice(topic: str) -> dict | None:
    """The rule walk's sentences to notice, the word underlined and not named,
    and the question that names the forms and states no rule; None for a topic
    with no walk or too few forms to contrast (`rulewalk.walk`'s notice step)."""
    from .lessontext import WALKS
    from .rulewalk import _question, sentence

    spec = WALKS.get(topic)
    if spec is None:
        return None
    found = [s for s in (sentence(topic, x) for x in spec.notice) if s]
    forms = list(dict.fromkeys(s["form"] for s in found))
    if len(forms) < 2:
        return None
    return {"examples": [{k: v for k, v in s.items()
                          if k not in ("name", "form_ru", "wrong", "wrong_tag")}
                         for s in found],
            "question_ru": _question(forms)}


# --------------------------------------------------------------------------
# Recording a session
# --------------------------------------------------------------------------

def start(now: datetime | None = None) -> dict:
    """Start today's session once; the same day returns the one started."""
    inputs = gather(now)
    session = compose(inputs)
    if not inputs.started:
        evidence.record(STARTED, {"today": session.today, "unit": session.unit,
                                  "topic": session.topic, "n": session.n,
                                  "emphasis": session.emphasis, "seed": session.seed,
                                  "steps": [s.id for s in session.steps]})
    return session.to_dict()


def finish_step(session_id: str, step: str, *, asked: int, correct: int,
                skipped: int = 0, now: datetime | None = None) -> dict:
    """A step is done: say so in the log, and finish the session after its last."""
    if step not in NAMES:
        raise ValueError(f"no such step: {step}")
    today_, unit, third = session_id.split(":")
    evidence.record(STEP_DONE, {"session": session_id, "today": today_, "unit": unit,
                                "step": step, "asked": asked, "correct": correct,
                                "skipped": skipped})
    inputs = gather(now, topic=None if third.isdigit() else third)
    session = compose(inputs)
    if session.kind == "today" and session.id == session_id and session.done:
        with evidence.connect() as log:
            already = any(e.payload.get("session") == session_id
                          for e in evidence.since(log, (DONE,), day_start(local_day(now))))
        if not already:
            evidence.record(DONE, {"session": session_id, "today": today_, "unit": unit,
                                   "n": session.n, "emphasis": session.emphasis})
    return {"session": session.to_dict(), "next": next_task(inputs, session)}


# --------------------------------------------------------------------------
# The hint: what code can say about a first miss without giving the answer
# --------------------------------------------------------------------------

def _distance(a: str, b: str) -> int:
    """Levenshtein distance, for telling a slip from another form."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def hint(item: dict, given: str) -> str:
    """One Russian sentence from code for a first miss, never the key itself.

    In order: the word's dictionary form typed where the sentence needs another;
    another real form of the right word (with the rule the item is keyed by, the
    first sentence of its `why_ru`); a slip in spelling near the key; else that
    rule, or the form asked for.
    """
    import re

    from .item import accepts

    said = (given or "").strip().casefold()
    keys = [k.strip().casefold() for k in (item.get("answer") or "").split("~") if k.strip()]
    if not said or not keys:
        return "Впиши ответ — тогда проверю."
    if accepts(item.get("answer") or "", given):
        return ""
    why = (item.get("why_ru") or "").strip()
    rule = re.split(r"(?<=[.!?])\s+", why)[0] if why else ""
    # A rule that spells the key would answer the item: it is kept back.
    plain = re.sub(r"[*«»]", "", rule).casefold()
    if any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", plain) for k in keys):
        rule = ""
    lemma = (item.get("lemma") or "").casefold()
    near = min(keys, key=lambda k: _distance(said, k))
    if lemma and said == lemma and near != lemma:
        return ("Это словарная форма, а здесь слово стоит в другой форме."
                + (f" {rule}" if rule else ""))
    if lemma:
        try:
            from .morph import _readings

            same_word = any(found.casefold() == lemma for found, _tag in _readings(given.strip()))
        except Exception:  # noqa: BLE001 - no morphology means no such hint
            same_word = False
        if same_word:
            return "Слово верное, но форма другая." + (f" {rule}" if rule else "")
    if len(near) >= 4 and _distance(said, near) <= 2:
        start = next((i for i, (a, b) in enumerate(zip(said, near)) if a != b),
                     min(len(said), len(near)))
        where = "окончание" if start >= len(near) - 3 else "основу"
        return f"Почти: проверь {where} слова."
    if rule:
        return f"Подсказка: {rule}"
    label = (item.get("hint") or "").split(", ")[-1]
    return f"Нужна форма: {label}." if label else "Попробуй ещё раз."


# --------------------------------------------------------------------------
# Words: signed apart from drills
# --------------------------------------------------------------------------

def sign_word(word: dict) -> str:
    """A token for one word item. It carries no `item`, so `itemref.verify` (and
    with it every drill's answer endpoint) refuses it."""
    from . import identity
    from .itemref import _sign

    return _sign({"ref": {"kind": "session-word", "v": 1,
                          "learner": identity.current().learner}, "word": word})


def verify_word(token: str) -> dict:
    from .itemref import _verify

    payload = _verify(token)
    if not isinstance(payload, dict) or not isinstance(payload.get("word"), dict):
        raise ValueError("not a word token")
    return payload["word"]


def word_items(words_db: sqlite3.Connection, lemmas: tuple[str, ...], count: int,
               seed: int) -> list[dict]:
    """The unit's words in EKI's phrases: the phrase with the word's form gapped,
    the word's Russian and the phrase's. A word with no phrase that shows it as
    one whole word is left out."""
    import random
    import re

    from .evs import ATTRIBUTION, SOURCE_ID, examples
    from .meaning import russian
    from .morph import _readings

    rng = random.Random(seed)
    order = list(lemmas)
    rng.shuffle(order)
    out = []
    for lemma in order:
        if len(out) >= count:
            break
        phrases = [p for p in examples(words_db, lemma)
                   if not any(m in p["et"] for m in ("{", "/", "...", "…", "(", "["))
                   and 2 <= len(p["et"].split()) <= 9]
        chosen = None
        for p in phrases:
            for m in re.finditer(r"[\wÕÄÖÜŠŽõäöüšž-]+", p["et"]):
                try:
                    readings = _readings(m.group())
                except Exception:  # noqa: BLE001
                    readings = []
                if any(found == lemma for found, _tag in readings):
                    chosen = (p, m)
                    break
            if chosen:
                break
        if chosen is None:
            continue
        p, m = chosen
        try:
            meaning, _ = russian(words_db, lemma)
        except Exception:  # noqa: BLE001
            meaning = []
        if not meaning:
            continue
        form = m.group()
        out.append({"lemma": lemma, "answer": form,
                    "prompt": p["et"][:m.start()] + "____" + p["et"][m.end():],
                    "lemma_ru": ", ".join(meaning[:2]), "sentence_ru": p["ru"],
                    "source_id": SOURCE_ID, "attribution": ATTRIBUTION})
    return out


def answer_word(token: str, given: str, attempt: int) -> dict:
    """Grade one word; the first correct recall puts it in review (ADR-0009)."""
    from . import config, review
    from .item import accepts

    word = verify_word(token)
    correct = accepts(word["answer"], given)
    evidence.record(WORD, {"lemma": word["lemma"], "prompt": word["prompt"],
                           "expected": word["answer"], "answer": given,
                           "correct": correct, "attempt": attempt})
    queued = False
    if correct and attempt == 1:
        rev = review.connect(config.learner_db("REVIEW_DB"))
        if not _vocab_cards(rev, (word["lemma"],)):
            review.add(rev, kind="vocab", lemma=word["lemma"], tag="meaning",
                       prompt=f"«{word['lemma']}» — mida see tähendab?",
                       answer=word["lemma_ru"], source="session",
                       context=word["prompt"].replace("____", word["answer"]),
                       source_id=word.get("source_id"))
            queued = True
    out = {"correct": correct, "queued": queued}
    if correct or attempt > 1:
        out |= {"answer": word["answer"], "lemma": word["lemma"],
                "lemma_ru": word["lemma_ru"]}
    else:
        out["hint_ru"] = hint({"answer": word["answer"], "lemma": word["lemma"]}, given)
    return out


# --------------------------------------------------------------------------
# Placement: at most twelve items, placing by unit (ADR-0009)
# --------------------------------------------------------------------------

#: Items per probed unit, and probes: twelve items at most.
PLACE_ITEMS = 3
PLACE_ROUNDS = 4
#: Right answers of `PLACE_ITEMS` that count a unit as known.
PLACE_PASS = 2


def placeable() -> list[str]:
    """Units a placement may probe, in order: those with a typed, drillable core
    topic (unit 1's sounds are heard, and every learner may start there)."""
    from .curriculum import by_id
    from .practice import HEARD, missing_here
    from .units import UNITS

    absent = missing_here()
    out = []
    for u in UNITS:
        if any(by_id(t).generator and by_id(t).generator not in HEARD and t not in absent
               for t in u.topics) and u.n > 1:
            out.append(u.id)
    return out


def probe_topics(unit_id: str) -> list[str]:
    """A unit's typed, drillable core topics, in its order: what a probe asks."""
    from .curriculum import by_id
    from .practice import HEARD, missing_here
    from .units import by_id as unit_by_id

    absent = missing_here()
    return [t for t in unit_by_id(unit_id).topics
            if by_id(t).generator and by_id(t).generator not in HEARD and t not in absent]


def place(results: list[tuple[str, bool]]) -> dict:
    """Binary search over the placeable units from the answers so far.

    `results` is (unit, correct) per answered item, in order; a unit's probe is
    answered whole. Returns the next unit to probe, or `done` with the unit to
    start at: the first unit not shown to be known. Nothing here awards mastery;
    the placement is navigation."""
    units = placeable()
    lo, hi = 0, len(units)
    asked: dict[str, list[bool]] = {}
    for unit, ok in results:
        asked.setdefault(unit, []).append(ok)
    rounds = 0
    while lo < hi and rounds < PLACE_ROUNDS:
        mid = (lo + hi) // 2
        answers = asked.get(units[mid])
        if not answers:
            return {"done": False, "unit": units[mid], "asked": len(results),
                    "left": PLACE_ITEMS}
        # A probe has its three items, or fewer where the generator had fewer:
        # two of three, in proportion.
        if sum(answers) * PLACE_ITEMS >= PLACE_PASS * len(answers):
            lo = mid + 1
        else:
            hi = mid
        rounds += 1
    start_at = units[lo] if lo < len(units) else units[-1]
    from .units import UNITS, by_id

    # A learner shown to know nothing starts at the very beginning, unit 1.
    if lo == 0:
        start_at = UNITS[0].id
    return {"done": True, "start": start_at, "asked": len(results),
            "skip": [u.id for u in UNITS if u.n < by_id(start_at).n]}


def record_placement(results: list[dict], start_at: str) -> evidence.Event:
    return evidence.record(PLACED, {"items": results, "start": start_at})
