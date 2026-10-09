"""The unit check: the checked half of a unit's completion (ADR-0007).

Five items per core topic and per revisited rule, graded by the server, which
rebuilds the set from its seed. A unit is **complete** when its core topics are
mastered and its check is passed; reading, listening, speaking and writing tasks
never gate it.

- **Pass:** every part at least 4 of 5. Across a unit, unprompted, with no clue
  which rule applies, the bar sits between the checkpoint's 75 % and test-out's
  5 of 5.
- **A part answered 5 of 5 masters its topic**, as a test-out would: someone who
  already knows a unit can complete it from its check. A revisit masters nothing:
  its topic was mastered on its own rules.
- **A failed check takes nothing away.** Answers are recorded like any probe's,
  and misses join the review queue.
- **Revision units** with a stage checkpoint (19, 30) run that checkpoint; one
  without (27) checks the topics its stage has introduced so far, the most recent
  first. A unit with nothing drillable has no check (`NO_CHECK`).
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from . import evidence

PER_PART = 5
PART_PASS = 4

#: The most topics a revision unit without a checkpoint asks.
REVISION_PARTS = 4

#: Units whose core topics have no drill yet, so nothing can be checked.
NO_CHECK: dict[str, str] = {
    "plaanid": "`tulevik` has no generator yet (docs/course-structure.md)",
    "too-elu": "`liitsonad` has no generator yet (docs/course-structure.md)",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS unit_checks (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    unit    TEXT NOT NULL,
    asked   INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    passed  INTEGER NOT NULL,
    at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_unit_checks_unit ON unit_checks(unit, id);
"""

Part = tuple[str, tuple[str, ...] | None]


def _drillable(topic: str) -> bool:
    from .curriculum import by_id
    from .practice import missing_here

    return by_id(topic).generator is not None and topic not in missing_here()


def parts(unit) -> list[Part]:
    """What the unit's check asks: `(topic, rules)` per part, or one
    `("checkpoint:<level>", None)` for a revision unit carrying a checkpoint."""
    if unit.checkpoint and not unit.topics:
        return [(f"checkpoint:{unit.checkpoint}", None)]
    out: list[Part] = [(t, None) for t in unit.topics if _drillable(t)]
    out += [(r.topic, tuple(r.rules)) for r in unit.revisits if _drillable(r.topic)]
    if out or unit.topics:
        return out
    from .units import UNITS

    earlier = [t for u in reversed(UNITS) if u.stage == unit.stage and u.n < unit.n
               for t in reversed(u.topics) if _drillable(t)]
    return [(t, None) for t in earlier[:REVISION_PARTS]]


def build(unit, seed: int) -> list[tuple[Part, object]]:
    """The check's items, each with its part, rebuilt identically from `seed`."""
    from .practice import items_for

    out: list[tuple[Part, object]] = []
    for n, part in enumerate(parts(unit)):
        topic, rules = part
        if topic.startswith("checkpoint:"):
            from .checkpoint import DEFAULT_ITEMS, build as checkpoint_items

            out += [(part, i) for i in checkpoint_items(topic.split(":", 1)[1],
                                                         count=DEFAULT_ITEMS, seed=seed)]
            continue
        items = items_for(topic, count=PER_PART, seed=seed + n, rules=rules)
        out += [(part, i) for i in items[:PER_PART]]
    return out


def grade(progress: sqlite3.Connection, unit, seed: int, given: list[str],
          reviews: sqlite3.Connection | None = None) -> dict:
    """Grade a whole check against the rebuilt set, record it, and say how it went."""
    from .checkpoint import PASS_MARK, save as save_checkpoint
    from .progress import is_mastered, mark_mastered, record

    items = build(unit, seed)
    if len(given) != len(items):
        raise ValueError(f"expected {len(items)} answers")
    tally: dict[Part, list[int]] = {}
    review: list[dict] = []
    for (part, item), said in zip(items, given):
        ok = item.check(said)
        record(progress, item, ok, answer=said)
        tally.setdefault(part, [0, 0])
        tally[part][0] += ok
        tally[part][1] += 1
        review.append({"prompt": item.prompt, "given": said, "answer": item.answer,
                       "solution": item.solution, "correct": ok, "topic": item.topic})
        if not ok and reviews is not None:
            from .handoff import queue_failed

            queue_failed(reviews, item)

    results = []
    for (topic, rules), (ok, n) in tally.items():
        if topic.startswith("checkpoint:"):
            level = topic.split(":", 1)[1]
            passed = save_checkpoint(progress, level, n, ok)
            results.append({"topic": topic, "rules": None, "asked": n, "correct": ok,
                            "passed": passed})
            continue
        passed = ok >= PART_PASS and n >= PER_PART
        if rules is None and ok == n == PER_PART and not is_mastered(progress, topic):
            mark_mastered(progress, topic, via="unit-check")
        results.append({"topic": topic, "rules": list(rules) if rules else None,
                        "asked": n, "correct": ok, "passed": passed})
    passed = save(progress, unit.id, results)
    return {"unit": unit.id, "passed": passed, "parts": results, "items": review,
            "pass_mark": PASS_MARK if unit.checkpoint and not unit.topics else None}


def save(progress: sqlite3.Connection, unit_id: str, results: list[dict]) -> bool:
    """Record a finished check; whether it passed is decided here, from the parts."""
    payload = {"unit": unit_id, "parts": results}
    ev = evidence.record("unit-checked", payload)
    return _save(progress, payload, ev.ts)


def _passed(results: Iterable[dict]) -> bool:
    results = list(results)
    return bool(results) and all(r.get("passed") for r in results)


def _save(progress: sqlite3.Connection, p: dict, at: str) -> bool:
    progress.executescript(SCHEMA)
    for r in p["parts"]:
        if "passed" not in r:   # an event written by `save` from parts alone
            r["passed"] = r["correct"] >= PART_PASS and r["asked"] >= PER_PART
    passed = _passed(p["parts"])
    with progress:
        progress.execute(
            "INSERT INTO unit_checks (unit, asked, correct, passed, at) VALUES (?,?,?,?,?)",
            (p["unit"], sum(r["asked"] for r in p["parts"]),
             sum(r["correct"] for r in p["parts"]), int(passed), at))
    return passed


@evidence.applies("unit-checked")
def _apply_unit_check(stores, ev) -> None:
    _save(stores["progress"], ev.payload, ev.ts)


def passed_units(progress: sqlite3.Connection) -> set[str]:
    progress.executescript(SCHEMA)
    return {r[0] for r in progress.execute(
        "SELECT DISTINCT unit FROM unit_checks WHERE passed = 1")}
