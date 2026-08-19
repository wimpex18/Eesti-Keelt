"""Should you sit the exam? An answer built only from evidence that exists.

## The question this exists to answer, and the date on it

The A2 sitting is **07.11.2026** and the decision is due **01.10.2026**. That is
a real deadline with a real cost either way: sitting too early wastes a fee and
a morning, sitting too late means the B1 attempt in spring 2027 has no rehearsal
behind it.

## What this refuses to do

**It does not predict a result.** No model here has seen a graded exam, there is
no population of candidates to calibrate against, and a number like "78 % likely
to pass" would be invented. The same refusal that keeps this project from
claiming IRT scores and pronunciation grades applies here, and it applies hardest
where the learner most wants a number.

What it does instead is report **what the evidence shows and what is missing**,
against the exam's own structure, and let a person decide.

## Why it reports four parts and never one total

The pass rule is **≥60 % overall AND no part scoring zero**. That second clause
is the trap: perfecting writing while never once practising listening can still
fail, and an aggregate percentage hides exactly that. So every part is reported
separately and an untouched part is called out as the risk it is, no matter how
strong the rest looks.

## The one part it cannot judge at all

**Rääkimine is paired and dialogic** — two candidates talking to each other,
negotiating agreement from a situation card. Nothing here simulates that. The app
can offer the question bank in the right shape and voice the other side with TTS,
and that is preparation, not assessment. It says so rather than scoring it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date

#: From the Notion plan. The optional A2 rehearsal and the date the decision is
#: due — both are the reason this module exists rather than a percentage.
DECIDE_BY = date(2026, 10, 1)
SITTING = date(2026, 11, 7)

#: The four parts, 25 points each, in the order the exam runs them.
PARTS = (
    ("kirjutamine", "Kirjutamine", "письмо"),
    ("kuulamine", "Kuulamine", "аудирование"),
    ("lugemine", "Lugemine", "чтение"),
    ("raakimine", "Rääkimine", "говорение"),
)

#: Enough practice in a part that "they have never done this" is no longer true.
#: Not a competence threshold — a *contact* threshold, which is all an activity
#: count can honestly support.
CONTACT = 3


@dataclass(frozen=True)
class Part:
    id: str
    et: str
    ru: str
    #: What was actually counted, in plain terms.
    evidence: str
    #: True when there is contact, False when there is none, None when the app
    #: cannot tell — which is different from "none" and must not be shown as it.
    touched: bool | None
    note: str = ""


@dataclass
class Readiness:
    level: str
    parts: list[Part]
    grammar: dict
    vocabulary: dict
    verdict: str
    reasons: list[str] = field(default_factory=list)
    days_to_decide: int = 0
    days_to_sitting: int = 0

    @property
    def countdown(self) -> str:
        """The one number that motivates without lying.

        A streak rewards attendance and collapses the week someone falls ill.
        A date does not move, does not judge, and does not reset — it is simply
        true, and it is the fact that actually applies pressure.
        """
        if self.days_to_decide > 0:
            return f"до решения {self.days_to_decide} дн."
        if self.days_to_sitting > 0:
            return f"до экзамена {self.days_to_sitting} дн."
        return "дата прошла"

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "countdown": self.countdown,
            "parts": [vars(p) for p in self.parts],
            "grammar": self.grammar,
            "vocabulary": self.vocabulary,
            "verdict": self.verdict,
            "reasons": self.reasons,
            "days_to_decide": self.days_to_decide,
            "days_to_sitting": self.days_to_sitting,
            # Russian, because this is the sentence that stops a number
            # being over-read six weeks before a registration deadline. A
            # caveat the reader cannot read is not a caveat.
            "caveat": (
                "Это не прогноз результата экзамена — это то, что сделано, и "
                "то, что не тронуто. Говорение (rääkimine) оценить нельзя: на "
                "экзамене говорят в паре."
            ),
        }


def _grammar(progress: sqlite3.Connection, level: str) -> dict:
    from .checkpoint import passed_levels
    from .curriculum import TOPICS
    from .progress import is_mastered

    topics = [t for t in TOPICS if t.level == level and t.generator]
    mastered = [t.id for t in topics if is_mastered(progress, t.id)]
    return {
        "topics": len(topics),
        "mastered": len(mastered),
        "outstanding": [t.id for t in topics if t.id not in mastered],
        "checkpoint_passed": level in passed_levels(progress),
    }


def _vocabulary(vocabulary, words, level: str) -> dict:
    """Words met at this level, against what the level contains.

    A count rather than a verdict: knowing every A2 word does not make anyone
    ready, and meeting few of them does not make the exam impossible.
    """
    if vocabulary is None or words is None:
        return {"known": 0, "level_words": 0, "measured": False}
    total = words.execute(
        "SELECT COUNT(*) FROM words WHERE proficiency = ?", (level,)
    ).fetchone()[0]
    try:
        known = vocabulary.execute(
            "SELECT COUNT(*) FROM vocab_status WHERE known = 1"
        ).fetchone()[0]
    except sqlite3.Error:
        known = 0
    return {"known": known, "level_words": total, "measured": True}


def _official(content, level: str) -> dict[str, int]:
    """How much official material exists per exam part at this level.

    This is what turns "practise listening" into "there are five official A2
    listening tasks, here they are". Nothing of HARNO's is stored — these are
    the indexed pointers — so the count is of links, not of content.
    """
    if content is None:
        return {}
    try:
        rows = content.execute(
            """SELECT i.skill, COUNT(*) n FROM items i
               JOIN sources s ON s.id = i.source_id
               WHERE i.level = ? AND s.id IN ('harno', 'eis')
               GROUP BY i.skill""",
            (level,),
        ).fetchall()
    except sqlite3.Error:
        return {}
    return {r["skill"]: r["n"] for r in rows}


def _parts(progress: sqlite3.Connection, level: str,
           content=None) -> list[Part]:
    from .library import exposure, seen_items
    from .notion import connect as notion_connect

    out: list[Part] = []
    seen = seen_items(progress)
    read = exposure(progress)
    official = _official(content, level)

    def material(skill: str) -> str:
        n = official.get(skill, 0)
        return f" · {n} офиц. заданий" if n else ""

    # Writing: corrections queued for the error log are the only durable trace
    # a writing check leaves, which makes them the honest count here.
    try:
        from . import app as _app

        queued = notion_connect(_app.NOTION_DB).execute(
            "SELECT COUNT(*) FROM notion_queue"
        ).fetchone()[0]
    except Exception:  # noqa: BLE001 - absence is a valid answer, not an error
        queued = 0

    out.append(Part(
        "kirjutamine", "Kirjutamine", "письмо",
        evidence=f"{queued} исправлений в логе" + material("kirjutamine"),
        touched=queued >= CONTACT if queued else False,
        note="На экзамене четыре задания по письму.",
    ))
    out.append(Part(
        "kuulamine", "Kuulamine", "аудирование",
        evidence=f"{len(seen)} текстов открыто" + material("kuulamine"),
        touched=len(seen) >= CONTACT,
    ))
    out.append(Part(
        "lugemine", "Lugemine", "чтение",
        evidence=(f"{read['items']} текстов, {read['minutes']} мин"
                  + material("lugemine")),
        touched=read["items"] >= CONTACT,
    ))
    out.append(Part(
        "raakimine", "Rääkimine", "говорение",
        evidence="не измеряется" + material("raakimine"),
        # Not False. "We cannot tell" and "you have done none" are different
        # claims, and showing the first as the second would be a lie the learner
        # would reasonably act on.
        touched=None,
        note="На экзамене говорят в паре — приложение это оценить не может. "
             "Тренируйся с банком вопросов и TTS.",
    ))
    return out


def readiness(
    level: str = "A2",
    progress: sqlite3.Connection | None = None,
    vocabulary: sqlite3.Connection | None = None,
    words: sqlite3.Connection | None = None,
    content: sqlite3.Connection | None = None,
    today: date | None = None,
) -> Readiness:
    """Evidence for and against sitting `level`, with the reasons named."""
    today = today or date.today()
    grammar = _grammar(progress, level) if progress is not None else {}
    parts = _parts(progress, level, content) if progress is not None else []
    vocab = _vocabulary(vocabulary, words, level)

    reasons: list[str] = []
    untouched = [p for p in parts if p.touched is False]
    if untouched:
        reasons.append(
            "Не тронутые части экзамена: "
            + ", ".join(f"{p.et} ({p.ru})" for p in untouched)
            + ". Ни одна часть не может быть нулевой."
        )
    if grammar and grammar["outstanding"]:
        reasons.append(
            f"Тем уровня {level} ещё не пройдено: "
            f"{len(grammar['outstanding'])} — "
            + ", ".join(grammar["outstanding"][:5])
        )
    if grammar and not grammar["checkpoint_passed"]:
        reasons.append(f"Контрольная работа {level} не сдана.")

    if not grammar:
        verdict = "teadmata"
    elif not reasons:
        verdict = "tõendid toetavad"
    elif untouched or len(reasons) > 1:
        verdict = "ei ole veel"
    else:
        verdict = "peaaegu"

    return Readiness(
        level=level,
        parts=parts,
        grammar=grammar,
        vocabulary=vocab,
        verdict=verdict,
        reasons=reasons,
        days_to_decide=(DECIDE_BY - today).days,
        days_to_sitting=(SITTING - today).days,
    )
