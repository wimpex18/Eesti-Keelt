"""Test-out and placement: starting where you are, not at lesson one.

Step 4 of the curriculum plan, and it is deliberately cheap, because step 3
already built the thing it needs. A topic marked known by a placement probe and
a topic mastered by practice differ only in a `via` column, so this module runs
probes and calls `progress.mark_mastered`; it owns no state of its own.

## Two features, one mechanism

**Test-out** is a short probe of one topic: get every item right and the topic is
marked known without working through it. **Placement** is the same probe run
across the syllabus in study order until the learner starts failing, which
answers "where do I begin" for someone who is not a beginner.

## Why the bar is higher than the practice gate

Practice masters a topic on 8 of the last 10. A test-out demands **5 of 5**.
That looks inconsistent and is not: the two are buying different things. Ten
attempts with two mistakes is a learner who has worked through a topic and
mostly holds it. Five attempts is thin evidence, and it is being used to skip
the work entirely, so the only defensible reading of a wrong answer is "not yet".
A false pass here costs more than a false fail — it silently removes a topic
from the course and unlocks everything downstream of it — while a false fail
costs one session of practice the learner did not strictly need.

Probe attempts are recorded as ordinary attempts, because that is what they are.
A learner who fails a test-out has genuinely answered those items, and the
rolling window should know.

## This is not IRT, and says so

The plan floated item-response theory: ask progressively harder items, and the
level where the learner fails is the entry point. The adaptive half of that is
here — the sweep walks the syllabus in order and stops once failures accumulate
— but the *psychometric* half is not, because IRT needs per-item difficulty
parameters estimated from a population of test-takers, and this app has one user.
Calling a stopping rule "IRT" would be dressing up a heuristic. What the sweep
actually relies on is the prerequisite graph: study order already encodes
difficulty, because a topic that depends on four others is genuinely later.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable, Iterable

from .config import LEVELS

# Five items, all five correct. See the module docstring for why this is
# stricter than the 8-of-10 practice gate rather than inconsistent with it.
PROBE_ITEMS = 5
PROBE_REQUIRED = 5

# How many topics in a row may fail before the sweep concludes it has found the
# learner's level. One failure can be a bad item or a slip; two in a row in an
# ordered syllabus is a boundary.
STOP_AFTER_FAILURES = 2

Ask = Callable[[object], str]


@dataclass(frozen=True)
class ProbeResult:
    topic: str
    asked: int
    correct: int
    passed: bool
    skipped: str = ""      # why no probe ran, if none did

    @property
    def ran(self) -> bool:
        return not self.skipped


def probe(
    progress: sqlite3.Connection,
    topic: str,
    ask: Ask,
    count: int = PROBE_ITEMS,
    required: int = PROBE_REQUIRED,
    seed: int | None = None,
) -> ProbeResult:
    """Ask a short set on one topic; mark it known only on a clean sweep.

    `ask` is injected rather than reading stdin here, so the same code serves the
    CLI, a future web route, and the tests without any of them pretending to be
    a terminal.
    """
    from .practice import items_for
    from .progress import is_mastered, mark_mastered, record

    if is_mastered(progress, topic):
        return ProbeResult(topic, 0, 0, True, skipped="already known")

    try:
        items = items_for(topic, count=count, seed=seed)
    except ValueError as exc:  # no generator for this topic
        return ProbeResult(topic, 0, 0, False, skipped=str(exc))
    if not items:
        return ProbeResult(topic, 0, 0, False, skipped="generator produced nothing")

    correct = 0
    for item in items:
        given = ask(item)
        ok = item.check(given)
        correct += ok
        record(progress, item, ok, answer=given)

    passed = correct >= required and len(items) >= required
    if passed:
        mark_mastered(progress, topic, via="placement")
    return ProbeResult(topic, len(items), correct, passed)


def candidates(
    progress: sqlite3.Connection,
    levels: tuple[str, ...] = LEVELS,
) -> list:
    """Topics worth probing right now, in study order.

    Recomputed as the sweep goes, because passing `gen-stem` unlocks eleven
    topics that were not offerable a moment earlier.
    """
    from .curriculum import available
    from .progress import unlocked

    return [
        topic
        for topic in available(unlocked(progress))
        if topic.generator and topic.level in levels
    ]


def sweep(
    progress: sqlite3.Connection,
    ask: Ask,
    levels: tuple[str, ...] = LEVELS,
    stop_after: int = STOP_AFTER_FAILURES,
    seed: int | None = None,
    on_result: Callable[[ProbeResult], None] | None = None,
) -> list[ProbeResult]:
    """Walk the syllabus until the learner starts failing; that is where to start.

    Stops on consecutive failures rather than on the first one, so a single bad
    item or a slip does not end the placement early and leave a learner doing
    A1 material they know.
    """
    results: list[ProbeResult] = []
    consecutive = 0
    seen: set[str] = set()

    while consecutive < stop_after:
        pending = [t for t in candidates(progress, levels) if t.id not in seen]
        if not pending:
            break
        topic = pending[0]
        seen.add(topic.id)

        result = probe(progress, topic.id, ask, seed=seed)
        results.append(result)
        if on_result is not None:
            on_result(result)

        if not result.ran:
            continue
        consecutive = 0 if result.passed else consecutive + 1
    return results


def entry_point(results: Iterable[ProbeResult]) -> str | None:
    """The first topic the learner actually failed — where the course begins."""
    for result in results:
        if result.ran and not result.passed:
            return result.topic
    return None
