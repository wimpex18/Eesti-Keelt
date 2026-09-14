"""Test-out and placement: starting where you are, not at lesson one.

Runs probes and calls `progress.mark_mastered`; owns no state.

- **Test-out** probes one topic; all items right marks it known.
- **Placement** probes the syllabus in study order.
- **The bar is 5 of 5**, higher than practice's 8 of 10: a false pass silently
  removes a topic and unlocks everything after it; a false fail costs one
  session.
- **A failure prunes only dependants.** The syllabus is a graph, so failing a
  noun topic says nothing about verbs; the result is a set of entry points.
  `MAX_FAILURES` and `MAX_PROBES` bound the session.
- Probe attempts are recorded as ordinary attempts.
- Not IRT: there is no calibrated item population; difficulty comes from the
  prerequisite graph.
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

# A failure prunes the topics that depend on it. A sweep ends after this many
# failed topics or this many probes, whichever comes first.
MAX_FAILURES = 3
MAX_PROBES = 12

Ask = Callable[[object], str]


class Stopped(Exception):
    """Nobody is answering: end of input, or Ctrl-C.

    Raised, never returned as a blank answer: a blank grades as wrong, and wrong
    answers written for items nobody saw would feed mastery, checkpoints and the
    readiness verdict.
    """


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
    """Ask a short set on one topic; mark it known only on a clean sweep. `ask` is
    injected, so the CLI and tests share this code.
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
    """Topics worth probing right now, in study order — recomputed as passes unlock more."""
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
    """Probe the syllabus, pruning each failed topic's dependants and continuing on
    independent branches.
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

        try:
            result = probe(progress, topic.id, ask, seed=seed)
        except Stopped:
            # Stop on Ctrl-C/EOF: answered topics stay recorded; the interrupted topic yields
            # no result.
            break
        results.append(result)
        if on_result is not None:
            on_result(result)

        if not result.ran:
            continue
        if not result.passed:
            failures += 1
            # Everything downstream rests on what was just missed.
            pruned |= set(unlocks(topic.id))
    return results


def entry_points(results: Iterable[ProbeResult]) -> list[str]:
    """Every topic the learner failed — one entry point per independent branch."""
    return [r.topic for r in results if r.ran and not r.passed]
