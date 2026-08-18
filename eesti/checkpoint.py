"""End-of-level checkpoints: a mixed quiz that is interleaved by construction.

Step 9, and the last piece of the curriculum plan. A checkpoint asks across
**every drillable topic at a level at once**, which makes it the one thing in
the app that is interleaved without having to be arranged: there is no blocked
version of "everything you learned at A1".

That is also what makes it a different measurement from the mastery gate. A
topic gate asks "can you do the conditional" immediately after ten conditionals,
when the rule is still in working memory and every item is the same shape. A
checkpoint asks fifteen questions in an order that gives no clue which rule
applies — which is the situation the exam creates, and the situation in which
people who have "mastered" every topic separately discover they cannot choose
between them.

## The pass mark is lower than the gate, and that is not a contradiction

Topic mastery wants 80 % on a blocked set. A checkpoint wants **75 %** across a
whole level, unprompted. The second is harder at the same number, so holding it
to the same bar would make finishing a level a rarer event than mastering every
topic in it — which would be backwards. The numbers differ because the tasks do.

## A failed checkpoint takes nothing away

It does not un-master anything. What it does is put the missed items into the
review queue, which is precisely the diagnosis it exists to produce: not "you do
not know A1" but "you know these topics and confuse these two". Mastery stays
where `progress.py` put it, and the review scheduler does the rest.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .config import LEVELS

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
        """Topics that went worse than the level as a whole — the diagnosis."""
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
    """A mixed set drawn across the level, dealt round-robin so no rule repeats.

    Round-robin rather than random: a random draw from a level with nine verb
    topics and three noun topics produces a quiz that is mostly verbs, and the
    learner would be measured on what the syllabus happens to contain rather
    than on the level.
    """
    from .practice import items_for

    topics = topics_at(level)
    if not topics:
        return []

    per = max(1, count // len(topics) + 1)
    pools: dict[str, list] = {}
    for topic in topics:
        try:
            got = items_for(topic, count=per, seed=seed)
        except (ValueError, RuntimeError):
            continue
        if got:
            pools[topic] = got

    out: list = []
    while pools and len(out) < count:
        for topic in list(pools):
            if len(out) >= count:
                break
            out.append(pools[topic].pop(0))
            if not pools[topic]:
                del pools[topic]
    return out


def run(
    progress: sqlite3.Connection,
    level: str,
    ask: Ask,
    count: int = DEFAULT_ITEMS,
    seed: int | None = None,
    reviews: sqlite3.Connection | None = None,
) -> CheckpointResult:
    """Ask the mixed set, record every answer, and queue what was missed.

    Attempts are recorded as ordinary attempts — they are real graded answers —
    and missed items go into the review queue when one is supplied, because a
    checkpoint's value is the diagnosis, not the score.
    """
    from .progress import record

    progress.executescript(SCHEMA)
    items = build(level, count=count, seed=seed)
    if not items:
        return CheckpointResult(level, 0, 0, False, {})

    by_topic: dict[str, list[int]] = {}
    correct = 0
    for item in items:
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

    passed = correct / len(items) >= PASS_MARK
    with progress:
        progress.execute(
            "INSERT INTO checkpoints (level,asked,correct,passed,at)"
            " VALUES (?,?,?,?,?)",
            (level, len(items), correct, int(passed),
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
    return CheckpointResult(
        level, len(items), correct, passed,
        {t: (ok, n) for t, (ok, n) in by_topic.items()},
    )


def history(progress: sqlite3.Connection, level: str | None = None) -> list[sqlite3.Row]:
    progress.executescript(SCHEMA)
    sql = "SELECT * FROM checkpoints"
    params: tuple = ()
    if level:
        sql += " WHERE level = ?"
        params = (level,)
    return list(progress.execute(sql + " ORDER BY id DESC", params))


def passed_levels(progress: sqlite3.Connection) -> set[str]:
    progress.executescript(SCHEMA)
    return {
        r[0] for r in progress.execute(
            "SELECT DISTINCT level FROM checkpoints WHERE passed = 1"
        )
    } & set(LEVELS)
