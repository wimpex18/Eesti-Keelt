"""What the evidence says about the learner, for deciding what to do next.

Read-only summaries over the projections and the log, all arithmetic:

- **rule evidence:** per (topic, sub-rule), a recency-weighted accuracy (recent
  answers count more; half-life `HALF_LIFE_DAYS`) and how well its review
  cards are remembered right now (FSRS retrievability);
- **weak rules:** accuracy below `WEAK_ACCURACY` over at least `WEAK_MIN`
  answers, or cards remembered below `WEAK_RETRIEVABILITY`;
- **refresh:** a mastered topic whose cards are fading, or untouched for
  `STALE_DAYS`. Mastery is still not revoked; the planner brings the topic back;
- **skill balance:** practice per exam part over the last days, from the log;
- **recent mistakes:** wrong attempts as they were shown, for replaying.

Nothing here writes, and nothing here is a model's opinion.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

HALF_LIFE_DAYS = 14
WEAK_ACCURACY = 0.7
WEAK_MIN = 6
WEAK_RETRIEVABILITY = 0.8
REFRESH_RETRIEVABILITY = 0.7
STALE_DAYS = 60

#: Exam parts, and the log events that count as practice in each.
SKILL_EVENTS = {
    "kirjutamine": ("writing",),
    "kuulamine": ("dictation",),
    "lugemine": ("exposure",),
    "raakimine": ("speech",),
}


def _when(ts: str) -> datetime:
    at = datetime.fromisoformat(ts)
    return at if at.tzinfo else at.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class RuleEvidence:
    topic: str
    rule: str | None
    answers: int
    accuracy: float | None          # recency-weighted
    last_seen: str | None
    cards: int
    retrievability: float | None    # mean over the rule's cards, now

    @property
    def weak(self) -> bool:
        by_answers = (self.accuracy is not None and self.answers >= WEAK_MIN
                      and self.accuracy < WEAK_ACCURACY)
        by_memory = (self.retrievability is not None
                     and self.retrievability < WEAK_RETRIEVABILITY)
        return by_answers or by_memory


def _retrievability(review: sqlite3.Connection, now: datetime,
                    rules: set[tuple]) -> dict[tuple, list[float]]:
    """Retrievability of every grammar card now, grouped by (topic, rule).

    A card's tag is its sub-rule only in topics that have sub-rules (`rules`, as
    answered); elsewhere it is the hint text, and the card counts for the topic.
    """
    from fsrs import Card, Scheduler

    scheduler = Scheduler()
    out: dict[tuple, list[float]] = {}
    for r in review.execute("SELECT kind, tag, card FROM review_items WHERE kind != 'vocab'"):
        key = (r["kind"], r["tag"]) if (r["kind"], r["tag"]) in rules else (r["kind"], None)
        card = Card.from_dict(json.loads(r["card"]))
        out.setdefault(key, []).append(
            scheduler.get_card_retrievability(card, current_datetime=now))
    return out


def rule_evidence(progress: sqlite3.Connection, review: sqlite3.Connection,
                  now: datetime | None = None) -> list[RuleEvidence]:
    """One row per (topic, rule) the learner has answered or has cards for."""
    now = now or datetime.now(timezone.utc)
    weights: dict[tuple, list[tuple[float, int]]] = {}
    last: dict[tuple, str] = {}
    for r in progress.execute("SELECT topic, rule, correct, at FROM attempts"):
        key = (r["topic"], r["rule"] or None)
        age = max(0.0, (now - _when(r["at"])).total_seconds() / 86400)
        weights.setdefault(key, []).append((0.5 ** (age / HALF_LIFE_DAYS), r["correct"]))
        last[key] = max(last.get(key, ""), r["at"])
    memory = _retrievability(review, now, {k for k in weights if k[1]})

    out = []
    for key in sorted(set(weights) | set(memory), key=lambda k: (k[0], k[1] or "")):
        pairs = weights.get(key, [])
        total = sum(w for w, _ in pairs)
        cards = memory.get(key, [])
        out.append(RuleEvidence(
            topic=key[0], rule=key[1], answers=len(pairs),
            accuracy=(sum(w * c for w, c in pairs) / total) if total else None,
            last_seen=last.get(key), cards=len(cards),
            retrievability=(sum(cards) / len(cards)) if cards else None,
        ))
    return out


def weak_rules(evidence: list[RuleEvidence]) -> list[RuleEvidence]:
    """Weak rules, the documented #1 weakness (`obj-case`) first, then the weakest."""
    def weakness(e: RuleEvidence) -> float:
        return min(x for x in (e.accuracy, e.retrievability) if x is not None)

    return sorted((e for e in evidence if e.weak),
                  key=lambda e: (e.topic != "obj-case", weakness(e), e.topic, e.rule or ""))


def needs_refresh(progress: sqlite3.Connection, evidence: list[RuleEvidence],
                  now: datetime | None = None) -> list[str]:
    """Mastered topics whose cards are fading or that were left alone too long."""
    now = now or datetime.now(timezone.utc)
    out = []
    for r in progress.execute(
            "SELECT topic, last_seen FROM topic_state WHERE mastered_at IS NOT NULL"
            " ORDER BY topic"):
        cards = [e for e in evidence if e.topic == r["topic"] and e.retrievability is not None]
        weighted = sum(e.retrievability * e.cards for e in cards)
        n = sum(e.cards for e in cards)
        fading = n >= 3 and weighted / n < REFRESH_RETRIEVABILITY
        stale = bool(r["last_seen"]) and now - _when(r["last_seen"]) > timedelta(days=STALE_DAYS)
        if fading or stale:
            out.append(r["topic"])
    return out


def skill_activity(log: sqlite3.Connection, days: int = 7,
                   now: datetime | None = None) -> dict[str, int]:
    """How many practice events each exam part had in the last `days` days."""
    from . import evidence

    now = now or datetime.now(timezone.utc)
    after = (now - timedelta(days=days)).isoformat()
    counts = {}
    for part, types in SKILL_EVENTS.items():
        counts[part] = len(evidence.since(log, types, after))
    return counts


@dataclass(frozen=True)
class Mistake:
    event_id: str
    topic: str
    rule: str | None
    prompt: str
    expected: str
    answer: str
    at: str

    @property
    def solution(self) -> str:
        from .item import BLANK

        return self.prompt.replace(BLANK, self.expected)


def recent_mistakes(log: sqlite3.Connection, topic: str | None = None,
                    rule: str | None = None, limit: int = 5) -> list[Mistake]:
    """Wrong answers as they were shown, newest first: the log keeps the item."""
    rows = log.execute(
        "SELECT * FROM events WHERE type = 'attempt' ORDER BY seq DESC LIMIT 500")
    out = []
    for r in rows:
        p = json.loads(r["payload"])
        if p.get("correct") or not p.get("prompt"):
            continue
        if topic and p["topic"] != topic:
            continue
        if rule and p.get("rule") != rule:
            continue
        out.append(Mistake(r["id"], p["topic"], p.get("rule"), p["prompt"],
                           p["expected"], p.get("answer", ""), r["ts"]))
        if len(out) >= limit:
            break
    return out
