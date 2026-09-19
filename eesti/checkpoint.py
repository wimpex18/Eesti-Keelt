"""End-of-level checkpoints: a mixed quiz that is interleaved by construction.

A checkpoint asks across every drillable topic at a level at once, in an order
that gives no clue which rule applies — the exam's situation, unlike a topic
gate asked right after ten items of one rule.

- **Pass mark 75 %**, below the topic gate's 80 %: the same number is harder
  unprompted across a level.
- **A failed checkpoint takes nothing away.** Mastery stays; missed items go
  into the review queue, which is the diagnosis it exists to produce.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .config import LEVELS
# `Ask` is declared in both modules; `Stopped` is imported, never duplicated, so
# callers catch one exception class.

# Across a whole level, unprompted, with no clue which rule applies. Harder than
# a blocked topic set at the same number, so the bar is lower.
PASS_MARK = 0.75
DEFAULT_ITEMS = 15

SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    level   TEXT NOT NULL,
    asked   INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    passed  INTEGER NOT NULL,
    at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checkpoint_level ON checkpoints(level, id);
"""

Ask = Callable[[object], str]


@dataclass(frozen=True)
class CheckpointResult:
    level: str
    asked: int
    correct: int
    passed: bool
    by_topic: dict[str, tuple[int, int]]   # topic -> (correct, asked)

    @property
    def score(self) -> float:
        return self.correct / self.asked if self.asked else 0.0

    @property
    def weakest(self) -> list[str]:
        """Topics that went worse than the level as a whole. With one or two items per
        topic this points rather than proves; `by_topic` carries the tallies.
        """
        return sorted(
            (t for t, (ok, n) in self.by_topic.items() if n and ok / n < self.score),
            key=lambda t: self.by_topic[t][0] / self.by_topic[t][1],
        )


def topics_at(level: str) -> list[str]:
    """Drillable topics at a level, in study order."""
    from .curriculum import order

    return [t.id for t in order() if t.level == level and t.generator]


def ready(progress: sqlite3.Connection, level: str) -> bool:
    """Whether every drillable topic at this level has been mastered."""
    from .progress import mastered

    wanted = set(topics_at(level))
    return bool(wanted) and wanted <= mastered(progress)


def build(level: str, count: int = DEFAULT_ITEMS, seed: int | None = None) -> list:
    """A mixed set drawn across the level, dealt round-robin so no rule repeats and
    the level's topic mix does not skew the quiz.
    """
    from .practice import items_for

    topics = topics_at(level)
    if not topics:
        return []

    # Request per topic, and repeat passes until `count` is reached or pools run dry
    # (thin word lists otherwise under-deliver). Each pass deals round-robin; `seen`
    # prevents repeats.
    per = max(1, count // len(topics) + 1)
    out: list = []
    seen: set[tuple[str, str]] = set()
    ceiling = max(count * 8, 64)

    while len(out) < count and per <= ceiling:
        pools: dict[str, list] = {}
        for topic in topics:
            try:
                got = items_for(topic, count=per, seed=seed)
            except (ValueError, RuntimeError):
                continue
            fresh = [i for i in got if (i.topic, i.prompt) not in seen]
            if fresh:
                pools[topic] = fresh

        added = 0
        while pools and len(out) < count:
            for topic in list(pools):
                if len(out) >= count:
                    break
                # Never twice in a row from one topic: that is the whole point
                # of dealing rather than drawing, and a later pass must not
                # undo it at the seam.
                if out and len(pools) > 1 and out[-1].topic == topic:
                    continue
                item = pools[topic].pop(0)
                out.append(item)
                seen.add((item.topic, item.prompt))
                added += 1
                if not pools[topic]:
                    del pools[topic]

        if not added:
            break
        per *= 2
    return out


def run(
    progress: sqlite3.Connection,
    level: str,
    ask: Ask,
    count: int = DEFAULT_ITEMS,
    seed: int | None = None,
    reviews: sqlite3.Connection | None = None,
) -> CheckpointResult:
    """Ask the mixed set, record every answer, and queue what was missed."""
    from .progress import record

    progress.executescript(SCHEMA)
    items = build(level, count=count, seed=seed)
    if not items:
        return CheckpointResult(level, 0, 0, False, {})

    by_topic: dict[str, list[int]] = {}
    correct = 0
    for item in items:
        # `Stopped` propagates: an abandoned checkpoint writes no checkpoint row (which
        # would lower the readiness verdict) and queues nothing. An empty result is not
        # used because it already means "no items could be built". Answers given before
        # the stop stay recorded.
        given = ask(item)
        ok = item.check(given)
        correct += ok
        record(progress, item, ok, answer=given)
        tally = by_topic.setdefault(item.topic, [0, 0])
        tally[0] += ok
        tally[1] += 1
        if not ok and reviews is not None:
            from .handoff import queue_failed

            queue_failed(reviews, item)

    passed = save(progress, level, len(items), correct)
    return CheckpointResult(
        level, len(items), correct, passed,
        {t: (ok, n) for t, (ok, n) in by_topic.items()},
    )


def save(progress: sqlite3.Connection, level: str, asked: int, correct: int) -> bool:
    """Record a finished checkpoint; the pass mark is applied here, not by a caller."""
    progress.executescript(SCHEMA)
    passed = asked > 0 and correct / asked >= PASS_MARK
    with progress:
        progress.execute(
            "INSERT INTO checkpoints (level,asked,correct,passed,at)"
            " VALUES (?,?,?,?,?)",
            (level, asked, correct, int(passed),
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
    return passed


def passed_levels(progress: sqlite3.Connection) -> set[str]:
    progress.executescript(SCHEMA)
    return {
        r[0] for r in progress.execute(
            "SELECT DISTINCT level FROM checkpoints WHERE passed = 1"
        )
    } & set(LEVELS)
