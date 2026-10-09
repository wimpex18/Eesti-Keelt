"""After release: learners' answers and *Teata veast* reports retire items (ADR-0009, step 5).

The checks before release are code and one second model; the learners who
answer are the check after it. Three signals retire an item, each with its
own threshold:

- **split** — at least `SPLIT_MIN` answers, and one wrong answer given by at
  least `SPLIT_SHARE` of them: many people reading the text the same other
  way suggests a second right answer the key does not accept;
- **never varies** — at least `STEADY_MIN` answers, all right or all wrong: an
  item everybody gets right tests nothing, one nobody does is broken;
- **reported** — reports from `REPORTS_TO_RETIRE` different people, or one
  from the owner, who maintains the material.

Only permanent accounts (owner, learners) count towards retiring: a guest
sandbox is a name anyone can choose, so a few requests could otherwise retire
any item. Guests' answers and reports are kept and shown in `cli material
stats` all the same.

Retirement is sticky: an item retired once stays retired, even if later
answers would no longer meet the threshold; a corrected material comes back
under a new hash, and so a new id, with fresh statistics.

The store is the owner's `progress.db`, which every scope counts in (like the
daily allowances, `providers/budget.py`) and the state snapshot carries across
cold starts. It holds no learner's words: an answer is kept as the hash of its
normalised form, a reporter as the hash of their scope, and a report's note is
capped at `NOTE_CHARS`.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections import Counter
from datetime import datetime, timezone

SPLIT_MIN = 20
SPLIT_SHARE = 0.30
STEADY_MIN = 30
REPORTS_TO_RETIRE = 2
NOTE_CHARS = 300

#: What a *Teata veast* report says is wrong. Codes, shown in Russian by the page.
REASONS = {
    "vale-vastus": "ответ, который засчитывается, неверен",
    "mitu-vastust": "верных ответов больше одного",
    "viga-tekstis": "ошибка в тексте или вопросе",
    "muu": "другое",
}

#: The item id meaning the material as a whole (its text, not one question).
WHOLE = ""

SCHEMA = """
CREATE TABLE IF NOT EXISTS material_answers (
    material TEXT NOT NULL,
    item     TEXT NOT NULL,
    correct  INTEGER NOT NULL,
    answer   TEXT NOT NULL,      -- sha256 of the normalised answer, never the text
    counted  INTEGER NOT NULL,   -- 1 for owner and learners, 0 for guests
    at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_material_answers ON material_answers(material, item);
CREATE TABLE IF NOT EXISTS material_reports (
    material TEXT NOT NULL,
    item     TEXT NOT NULL,      -- '' for the material as a whole
    reason   TEXT NOT NULL,
    note     TEXT NOT NULL,
    reporter TEXT NOT NULL,      -- hash of the scope that reported
    kind     TEXT NOT NULL,      -- owner | learner | guest
    at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_material_reports ON material_reports(material, item);
CREATE TABLE IF NOT EXISTS material_retired (
    material TEXT NOT NULL,
    item     TEXT NOT NULL,
    why      TEXT NOT NULL,
    at       TEXT NOT NULL,
    PRIMARY KEY (material, item)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def ready(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.executescript(SCHEMA)
    return conn


def _retire(conn: sqlite3.Connection, material: str, item: str, why: str) -> None:
    conn.execute("INSERT OR IGNORE INTO material_retired VALUES (?,?,?,?)",
                 (material, item, why, _now()))


def record_answer(conn: sqlite3.Connection, material: str, item: str, *,
                  correct: bool, answer: str, permanent: bool) -> str | None:
    """Count one answer; the reason the item is now retired, if it is."""
    from ..comprehension import normalise

    ready(conn)
    with conn:
        conn.execute("INSERT INTO material_answers VALUES (?,?,?,?,?,?)",
                     (material, item, int(correct), _hash(normalise(answer)),
                      int(permanent), _now()))
        why = _answer_verdict(conn, material, item)
        if why:
            _retire(conn, material, item, why)
    return retired(conn, material).get(item)


def _answer_verdict(conn: sqlite3.Connection, material: str, item: str) -> str | None:
    from ..comprehension import normalise

    rows = conn.execute(
        "SELECT correct, answer FROM material_answers"
        " WHERE material = ? AND item = ? AND counted = 1", (material, item)).fetchall()
    n = len(rows)
    right = sum(r[0] for r in rows)
    if n >= STEADY_MIN and right in (0, n):
        return "never varies: " + ("everyone right" if right else "everyone wrong")
    blank = _hash(normalise(""))
    wrong = Counter(r[1] for r in rows if not r[0] and r[1] != blank)
    if n >= SPLIT_MIN and wrong:
        _, top = wrong.most_common(1)[0]
        if top / n >= SPLIT_SHARE:
            return f"answers split: {top} of {n} gave the same other answer"
    return None


def record_report(conn: sqlite3.Connection, material: str, item: str, *,
                  reason: str, note: str, scope) -> str | None:
    """Keep one *Teata veast* report; the reason the item is now retired, if it is."""
    if reason not in REASONS:
        raise ValueError(f"unknown reason {reason!r}")
    ready(conn)
    with conn:
        conn.execute("INSERT INTO material_reports VALUES (?,?,?,?,?,?,?)",
                     (material, item, reason, (note or "").strip()[:NOTE_CHARS],
                      _hash(f"{scope.kind}:{scope.id}"), scope.kind, _now()))
        rows = conn.execute(
            "SELECT DISTINCT reporter, kind FROM material_reports"
            " WHERE material = ? AND item = ? AND kind != 'guest'",
            (material, item)).fetchall()
        if any(kind == "owner" for _, kind in rows):
            _retire(conn, material, item, "reported by the owner")
        elif len(rows) >= REPORTS_TO_RETIRE:
            _retire(conn, material, item, f"reported by {len(rows)} people")
    return retired(conn, material).get(item)


def retired(conn: sqlite3.Connection, material: str) -> dict[str, str]:
    """item → why, for one material's retired items; `WHOLE` retires them all."""
    ready(conn)
    return {item: why for item, why in conn.execute(
        "SELECT item, why FROM material_retired WHERE material = ?", (material,))}


def summary(conn: sqlite3.Connection) -> list[dict]:
    """Per item: answers, share right, reports, retired — for `cli material stats`."""
    ready(conn)
    out: dict[tuple[str, str], dict] = {}
    for material, item, n, right, counted in conn.execute(
            "SELECT material, item, COUNT(*), SUM(correct), SUM(counted)"
            " FROM material_answers GROUP BY material, item"):
        out[(material, item)] = {"material": material, "item": item, "answers": n,
                                 "right": right, "counted": counted, "reports": 0,
                                 "retired": None}
    for material, item, n in conn.execute(
            "SELECT material, item, COUNT(*) FROM material_reports GROUP BY material, item"):
        out.setdefault((material, item), {"material": material, "item": item,
                                          "answers": 0, "right": 0, "counted": 0,
                                          "reports": 0, "retired": None})["reports"] = n
    for material, item, why in conn.execute(
            "SELECT material, item, why FROM material_retired"):
        out.setdefault((material, item), {"material": material, "item": item,
                                          "answers": 0, "right": 0, "counted": 0,
                                          "reports": 0, "retired": None})["retired"] = why
    return [out[k] for k in sorted(out)]
