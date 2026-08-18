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

## Failing one topic does not end the sweep

The first version stopped after two consecutive failures, and that was wrong in
a way worth recording, because it looked reasonable. The syllabus is a **graph,
not a line**: `osastav` and `mitmus` are nouns, `olevik` and `verb-form` are
verbs, and they are independent. A learner who is solid on verbs and shaky on
nouns — which is an ordinary way to be — failed two noun topics in a row and the
sweep concluded it had found their level without ever asking about a verb.

So a failure now prunes exactly what the graph says it should: the topics that
**depend on** the failed one. Failing `osastav` means not asking about `eitus`
or `obj-case`, because those are built on it and the answer is already known.
It means nothing at all about the verb branch, which keeps being probed.

That makes the result a **set** of entry points rather than one, which is the
honest shape: a learner can be at A2 on verbs and A1 on nouns, and a single
"you are here" cannot express that.

The cost is session length, so two budgets bound it — `MAX_FAILURES` and
`MAX_PROBES`. They are stopping rules for the learner's patience, not claims
about their level, and the sweep reports when it hit one.

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

# A failure prunes the topics that *depend* on the failed one, and nothing else.
# These two bound the session: a sweep ends when the learner has failed this many
# topics outright, or when it has asked this many probes, whichever comes first.
MAX_FAILURES = 3
MAX_PROBES = 12

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
    max_failures: int = MAX_FAILURES,
    max_probes: int = MAX_PROBES,
    seed: int | None = None,
    on_result: Callable[[ProbeResult], None] | None = None,
) -> list[ProbeResult]:
    """Probe the syllabus, pruning by the graph rather than stopping at the first wall.

    A failed topic removes its **dependants** from the sweep — they are built on
    it, so the answer is already known — and leaves every independent branch
    still to be asked about. That is what lets a learner who is strong on verbs
    and weak on nouns be placed correctly on both.
    """
    from .curriculum import unlocks

    results: list[ProbeResult] = []
    seen: set[str] = set()
    pruned: set[str] = set()
    failures = 0

    while failures < max_failures and len(results) < max_probes:
        pending = [
            t for t in candidates(progress, levels)
            if t.id not in seen and t.id not in pruned
        ]
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
        if not result.passed:
            failures += 1
            # Everything downstream rests on what was just missed. Asking about
            # it would only confirm what the failure already established.
            pruned |= set(unlocks(topic.id))
    return results


def entry_points(results: Iterable[ProbeResult]) -> list[str]:
    """Every topic the learner failed — one entry point per independent branch.

    A list rather than a single topic on purpose: being at A2 on verbs and A1 on
    nouns is an ordinary way to be, and one "you are here" cannot say it.
    """
    return [r.topic for r in results if r.ran and not r.passed]


def entry_point(results: Iterable[ProbeResult]) -> str | None:
    """The first branch to start on, or None if nothing was failed."""
    found = entry_points(results)
    return found[0] if found else None
