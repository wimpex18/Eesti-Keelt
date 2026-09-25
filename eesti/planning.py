"""Today's plan: what to do next, in what order, for how long, and why.

`plan()` is a pure function of `PlanInputs`: the same evidence on the same day
gives the same plan, so it can be tested with fixtures and explained line by
line. `gather()` reads the evidence; nothing here asks a model.

The time budget is filled in this order:

1. **Kordamine**: due reviews, at most `REVIEW_SHARE` of the budget. Forgetting
   is the cheapest loss to prevent.
2. **Repair**: the weakest rule (object case first, the documented #1 weakness),
   with the last mistake in it shown again.
3. **Refresh**: a mastered topic whose cards are fading.
4. **Skill floor**: the exam part practised least this week. A zero in any part
   fails the exam, so no part may be left untouched.
5. **New**: the next topic on the path, with whatever time is left.
6. **Reading**: when minutes remain, the next text within reach.

Every block carries its reason in Russian.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

REVIEW_SHARE = 0.4
MINUTES_PER_REVIEW = 0.5
REPAIR_MINUTES = 5
REFRESH_MINUTES = 4
SKILL_MINUTES = 5
MIN_BLOCK = 3

#: Exam parts: the tab that practises each, and its names.
SKILLS = {
    "kirjutamine": ("write", "Kirjutamine", "письмо"),
    "kuulamine": ("listen", "Kuulamine", "аудирование"),
    "lugemine": ("read", "Lugemine", "чтение"),
    "raakimine": ("speak", "Rääkimine", "говорение"),
}


@dataclass(frozen=True)
class Weak:
    topic: str
    topic_et: str
    rule: str | None
    accuracy: float | None
    answers: int
    retrievability: float | None
    mistake: dict | None = None     # the last wrong answer, as shown


@dataclass(frozen=True)
class PlanInputs:
    today: str
    due: int
    weak: tuple[Weak, ...] = ()
    refresh: tuple[tuple[str, str], ...] = ()       # (topic, topic_et)
    activity: dict = field(default_factory=dict)    # exam part -> events this week
    frontier: tuple[str, str] | None = None         # (topic, topic_et)
    reading: tuple[str, str] | None = None          # (item id, title)

    def digest(self) -> str:
        body = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(body.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Block:
    kind: str           # review | repair | refresh | skill | new | read
    minutes: int
    et: str             # what, in Estonian (the interface is exposure)
    ru: str             # its gloss
    why: str            # the reason, in Russian
    action: dict        # {"tab": ..., "topic": ..., "rules": [...], "item": ...}
    detail: dict | None = None


@dataclass(frozen=True)
class Plan:
    today: str
    minutes: int
    blocks: tuple[Block, ...]
    inputs: str         # `PlanInputs.digest()`, so a plan is traceable to its evidence

    def to_dict(self) -> dict:
        return {"today": self.today, "minutes": self.minutes, "inputs": self.inputs,
                "blocks": [asdict(b) for b in self.blocks]}


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{round(x * 100)}%"


def _count(n: int, one: str, few: str, many: str) -> str:
    tail = n % 100
    if 11 <= tail <= 14:
        return f"{n} {many}"
    return f"{n} {one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many}"


def plan(inputs: PlanInputs, minutes: int = 20) -> Plan:
    """Fill `minutes` with blocks, in the order the module docstring gives."""
    left = minutes
    blocks: list[Block] = []

    def add(block: Block) -> None:
        nonlocal left
        blocks.append(block)
        left -= block.minutes

    if inputs.due:
        want = max(MIN_BLOCK, math.ceil(inputs.due * MINUTES_PER_REVIEW))
        add(Block("review", min(want, math.floor(minutes * REVIEW_SHARE)) or MIN_BLOCK,
                  "Kordamine", "повторение",
                  f"К повторению {_count(inputs.due, 'карточка', 'карточки', 'карточек')}: "
                  "повторить вовремя проще, чем учить заново.",
                  {"tab": "review"}))

    if inputs.weak and left >= MIN_BLOCK:
        w = inputs.weak[0]
        facts = []
        from .learner import WEAK_ACCURACY, WEAK_MIN, WEAK_RETRIEVABILITY

        # Only the facts that make it weak: a strong half would read as a contradiction.
        if w.accuracy is not None and w.answers >= WEAK_MIN and w.accuracy < WEAK_ACCURACY:
            facts.append(f"точность {_pct(w.accuracy)} за последние недели "
                         f"({_count(w.answers, 'ответ', 'ответа', 'ответов')})")
        if w.retrievability is not None and w.retrievability < WEAK_RETRIEVABILITY:
            facts.append(f"карточки помнишь примерно на {_pct(w.retrievability)}")
        from .drills import RULE_ET

        # Only a rule with an Estonian name is named: a bare id (`question`) is a
        # database key, and the topic already says what is being drilled.
        rule = f" · {RULE_ET[w.rule]}" if w.rule in RULE_ET else ""
        add(Block("repair", min(REPAIR_MINUTES, left), f"{w.topic_et}{rule}",
                  "слабое правило",
                  "Слабое место: " + ", ".join(facts) + ".",
                  {"tab": "path", "topic": w.topic, "rules": [w.rule] if w.rule else None},
                  detail=w.mistake))

    if inputs.refresh and left >= MIN_BLOCK:
        topic, name = inputs.refresh[0]
        add(Block("refresh", min(REFRESH_MINUTES, left), name, "освежить",
                  "Тема пройдена, но начала забываться или давно не "
                  "встречалась.", {"tab": "path", "topic": topic}))

    if inputs.activity and left >= MIN_BLOCK:
        # Ties go to the order the exam runs the parts in.
        part = min(SKILLS, key=lambda p: (inputs.activity.get(p, 0), list(SKILLS).index(p)))
        tab, et, ru = SKILLS[part]
        n = inputs.activity.get(part, 0)
        add(Block("skill", min(SKILL_MINUTES, left), et, ru,
                  f"Меньше всего практики — в этой части экзамена: "
                  f"{_count(n, 'занятие', 'занятия', 'занятий')} за неделю. "
                  "Ни одна часть не должна быть нулём: иначе экзамен не сдать.",
                  {"tab": tab}))

    if inputs.frontier and left >= MIN_BLOCK:
        topic, name = inputs.frontier
        new = left if not inputs.reading or left < 2 * MIN_BLOCK + 2 else left - MIN_BLOCK - 2
        add(Block("new", new, name, "новая тема",
                  "Следующая тема на твоём пути (Rada).", {"tab": "path", "topic": topic}))

    if inputs.reading and left >= MIN_BLOCK:
        item, title = inputs.reading
        add(Block("read", left, title, "чтение",
                  "Текст, в котором больше всего знакомых тебе слов.",
                  {"tab": "read", "item": item}))

    # Minutes too few for a block of their own go to the last one.
    if blocks and left > 0:
        last = blocks[-1]
        blocks[-1] = Block(last.kind, last.minutes + left, last.et, last.ru, last.why,
                           last.action, last.detail)
    return Plan(inputs.today, minutes, tuple(blocks), inputs.digest())


def gather(now: datetime | None = None) -> PlanInputs:
    """The evidence a plan is made from, read from the learner's databases."""
    from . import config, evidence, learner, progress, review
    from .curriculum import by_id

    now = now or datetime.now(timezone.utc)
    prog = progress.connect(config.PROGRESS_DB)
    rev = review.connect(config.REVIEW_DB)
    with evidence.connect() as log:
        found = learner.rule_evidence(prog, rev, now)
        weak = []
        for e in learner.weak_rules(found)[:3]:
            last = learner.recent_mistakes(log, e.topic, e.rule, limit=1)
            weak.append(Weak(
                e.topic, by_id(e.topic).et, e.rule, e.accuracy, e.answers,
                e.retrievability,
                {"prompt": last[0].prompt, "expected": last[0].expected,
                 "answer": last[0].answer, "solution": last[0].solution}
                if last else None))
        activity = learner.skill_activity(log, now=now)
    due = rev.execute("SELECT COUNT(*) FROM review_items WHERE due <= ?",
                      (now.isoformat(),)).fetchone()[0]
    refresh = tuple((t, by_id(t).et) for t in learner.needs_refresh(prog, found, now))
    resume = progress.resume(prog)
    return PlanInputs(
        today=now.date().isoformat(), due=due, weak=tuple(weak), refresh=refresh,
        activity=activity,
        frontier=(resume, by_id(resume).et) if resume else None,
        reading=_next_text(),
    )


def _next_text() -> tuple[str, str] | None:
    """The top recommended text, or None without a corpus."""
    try:
        from .api.library import reading_next

        items = reading_next(limit=1).get("items") or []
    except Exception:  # noqa: BLE001 - reading is a suggestion, never a blocker
        return None
    return (items[0]["id"], items[0]["title"]) if items else None


def issue(minutes: int = 20, now: datetime | None = None) -> Plan:
    """Today's plan, recorded in the log when it differs from the last one issued
    today (so a page reload does not add an event)."""
    from . import evidence

    now = now or datetime.now(timezone.utc)
    made = plan(gather(now), minutes)
    with evidence.connect() as log:
        today = [e for e in evidence.since(log, ("plan-issued",), now.date().isoformat())]
    if not today or today[-1].payload.get("inputs") != made.inputs \
            or today[-1].payload.get("minutes") != minutes:
        evidence.record("plan-issued", made.to_dict())
    return made
