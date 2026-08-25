"""Should you sit the exam? An answer built only from evidence that exists.

## The question this exists to answer, and the date on it

**There is no target sitting right now, and that is a decision rather than an
omission.** The November 2026 A2 rehearsal was declined on 2026-08-20: the plan
is independent study plus a tutor through the winter, and an exam in 2027 —
either A2 and then B1, or B1 alone, whenever the evidence says ready.

So the countdown is off. That matters more than it sounds. A date that has been
declined is not a motivator, it is a reproach: every load of the app would have
shown "до регистрации N дн." toward a sitting the learner had already reasoned
their way out of. The honest version says no date is chosen and reports the
same evidence, which is what actually decides when to sit.

Set `TARGET` when a session is chosen and the countdown comes back. HARNO runs
quarterly and closes registration about five weeks ahead, so the shape of the
calendar is known even when the date is not.

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

#: The sitting being prepared for, or None while none is chosen.
#:
#: `(registration_closes, sitting)`. When set, `registration_closes` is **not**
#: a personal checkpoint that can slip — it is the day HARNO closes the list,
#: after which that sitting is gone until the next quarter whatever the learner
#: decides. It was once displayed as "до решения", which reads like a
#: self-imposed deadline: the one date in this app where a soft word could cost
#: an entire sitting.
#:
#: None as of 2026-08-20. The Q4 2026 A2 rehearsal (register by 01.10, sit
#: 07.11) was considered and declined in favour of another year's study, so
#: counting down to it would be counting down to a decision already made.
TARGET: tuple[date, date] | None = None

#: What the last considered session looked like, kept so setting a new one is
#: a matter of copying the shape rather than re-reading HARNO's calendar:
#: registration closes roughly five weeks before the sitting, quarterly.
EXAMPLE_TARGET = (date(2026, 10, 1), date(2026, 11, 7))


def _target() -> tuple[date | None, date | None]:
    return TARGET if TARGET else (None, None)

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
    #: The specific thing to open next. Counting official tasks tells a learner
    #: the shelf is stocked; naming one tells them what to do this evening, and
    #: only the second changes what happens.
    next_task: dict | None = None


@dataclass
class Readiness:
    level: str
    parts: list[Part]
    grammar: dict
    vocabulary: dict
    verdict: str
    reasons: list[str] = field(default_factory=list)
    days_to_decide: int | None = None
    days_to_sitting: int | None = None

    @property
    def countdown(self) -> str:
        """The one number that motivates without lying.

        A streak rewards attendance and collapses the week someone falls ill.
        A date does not move, does not judge, and does not reset — it is simply
        true, and it is the fact that actually applies pressure.
        """
        if self.days_to_decide is None:
            # No session chosen. Saying so beats counting down to one that was
            # declined, and beats an empty box that reads like a bug.
            return "экзамен ещё не выбран"
        if self.days_to_decide > 0:
            return f"до регистрации {self.days_to_decide} дн."
        if self.days_to_sitting > 0:
            return f"до экзамена {self.days_to_sitting} дн."
        return "дата прошла"

    def _deadline(self) -> dict | None:
        """The registration date, or None while no session is chosen.

        None rather than a placeholder: a caller that renders whatever it is
        given would otherwise print a date nobody is working toward.
        """
        decide, sitting = _target()
        if decide is None or sitting is None:
            return {
                "registration": None,
                "sitting": None,
                "note": (
                    "Сессия пока не выбрана. Экзамен планируется в 2027 году — "
                    "A2, затем B1, либо сразу B1. Дата ставится в "
                    "`readiness.TARGET`, и обратный отсчёт вернётся."
                ),
            }
        return {
            "registration": decide.isoformat(),
            "sitting": sitting.isoformat(),
            "note": (
                f"Регистрация на экзамен закрывается {decide:%d.%m.%Y}. "
                f"Экзамен {sitting:%d.%m.%Y}. Это не личный дедлайн: после "
                f"{decide:%d.%m.%Y} записаться на эту сессию уже нельзя."
            ),
        }

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
            # The deadline is external and hard, and the countdown alone does
            # not say so — registration closes weeks before a sitting, and
            # after it the date is not a choice any more. None while no
            # session is chosen; see `_deadline`.
            "deadline": self._deadline(),
        }


def _grammar(progress: sqlite3.Connection, level: str) -> dict:
    from .checkpoint import passed_levels
    from .curriculum import TOPICS
    from .progress import is_mastered

    topics = [t for t in TOPICS if t.level == level and t.generator]
    mastered = [t.id for t in topics if is_mastered(progress, t.id)]
    left = [t for t in topics if t.id not in mastered]
    return {
        "topics": len(topics),
        "mastered": len(mastered),
        # Names, not ids. `uhildumine` and `sonajark` are database keys with
        # the diacritics stripped; the things a learner has to go and study are
        # called **ühildumine** and **sõnajärg**, and the whole point of an
        # Estonian label in this app is that the term itself gets learned.
        #
        # This is the fourth place the same bug has been fixed -- `kusisonad`
        # on the path panel, `obj-case` in the review queue, `blocked_by` in
        # `/api/curriculum` -- and it is the one that reached furthest, because
        # `reasons` puts the list straight onto the readiness screen. Resolved
        # here for the same reason as the others: a page that has to turn ids
        # into names will eventually meet an id nobody taught it about.
        "outstanding": [t.et for t in left],
        # Kept as well, for a caller that needs identity rather than a label.
        "outstanding_ids": [t.id for t in left],
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


def _next_task(content, level: str, skill: str) -> dict | None:
    """One official task for this part, or None if there are none indexed.

    Restricted to actual **tasks**. Without that filter the first row by title
    for A2 listening was a consultation workbook — which is study material, not
    a rehearsal, and pointing someone at it under "you have never practised
    listening" is worse than the count it replaced. Naming the wrong thing is a
    stronger claim than naming nothing.

    First by title otherwise: HARNO numbers them, so "first" is the one the
    exam board put first rather than whichever row SQLite happened to return.
    """
    if content is None:
        return None
    try:
        row = content.execute(
            """SELECT i.title, i.meta FROM items i
               JOIN sources s ON s.id = i.source_id
               WHERE i.level = ? AND i.skill = ? AND s.id IN ('harno','eis')
                 AND (i.meta LIKE '%"kind": "ulesanne"%' OR i.meta NOT LIKE '%"kind"%')
               ORDER BY i.title LIMIT 1""",
            (level, skill),
        ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    import json as _json

    try:
        meta = _json.loads(row["meta"] or "{}")
    except ValueError:
        meta = {}
    return {"title": row["title"], "url": meta.get("url")}


def _parts(progress: sqlite3.Connection, level: str,
           content=None, notion=None) -> list[Part]:
    from .library import exposure, seen_items

    out: list[Part] = []
    seen = seen_items(progress)
    read = exposure(progress)
    official = _official(content, level)

    # Opened items, counted per exam part rather than in total. "You have
    # opened 14 texts" and "you have never opened a listening task" are
    # different facts, and only the second is what the no-part-may-be-zero rule
    # punishes.
    from .library import parts_touched

    touched = parts_touched(progress, content) if content is not None else {}

    def material(skill: str) -> str:
        n = official.get(skill, 0)
        return f" · {n} офиц. заданий" if n else ""

    # Writing: corrections queued for the error log are the only durable trace
    # a writing check leaves, which makes them the honest count here.
    #
    # Queued and sent are counted separately. While there was no way to push
    # from the app the distinction did not exist, and "N исправлений в логе"
    # described rows that had never reached the log. Both are contact; only one
    # is in the Vead database where the "three of a tag" rule can see it.
    #
    # The connection is passed in. It used to be opened from `app.NOTION_DB`
    # inside this function, which made the verdict depend on a module-level
    # path no caller could redirect: a test with its own fixtures still read
    # the developer's real queue, so the suite reported one thing locally and
    # another in CI. Same shape as every other path-frozen-at-import bug here.
    queued = pushed = 0
    if notion is not None:
        try:
            row = notion.execute(
                "SELECT COUNT(*) AS n, "
                "       COALESCE(SUM(pushed IS NOT NULL), 0) AS sent "
                "FROM notion_queue"
            ).fetchone()
            queued, pushed = row[0], row[1]
        except sqlite3.Error:
            pass  # absence is a valid answer, not an error

    writing = f"{queued} исправлений"
    if queued:
        writing += (f", из них {pushed} в логе Vead" if pushed
                    else ", ни одного ещё не отправлено в Vead")
    out.append(Part(
        "kirjutamine", "Kirjutamine", "письмо",
        evidence=writing + material("kirjutamine"),
        touched=queued >= CONTACT if queued else False,
        note="На экзамене четыре задания по письму.",
        next_task=_next_task(content, level, "kirjutamine"),
    ))
    # Listening counts two different things, and the second is the stronger of
    # the two. Opening a task means audio was played; a dictation means what
    # was said had to be written down and was scored against the transcript.
    # Either one is contact, but the evidence line says which happened, so
    # "I listened a lot" cannot quietly stand in for having been tested.
    try:
        from .dictation import stats as dictation_stats

        heard = dictation_stats(progress)
    except sqlite3.Error:
        heard = {"attempts": 0, "passed": 0, "accuracy": None}

    opened = touched.get("kuulamine", 0)
    evidence = f"{opened} заданий открыто"
    if heard["attempts"]:
        evidence += f" · {heard['passed']}/{heard['attempts']} диктантов"
        if heard["accuracy"] is not None:
            evidence += f", слов расслышано {heard['accuracy']:.0%}"
    out.append(Part(
        "kuulamine", "Kuulamine", "аудирование",
        evidence=evidence + material("kuulamine"),
        touched=opened >= CONTACT or heard["attempts"] >= CONTACT,
        next_task=_next_task(content, level, "kuulamine"),
    ))
    out.append(Part(
        "lugemine", "Lugemine", "чтение",
        # Per part, like the others. `exposure` counts every item opened, so
        # a learner who had only ever played listening tasks was credited with
        # reading -- which is exactly the confusion the no-part-may-be-zero
        # rule punishes. Minutes stay from `exposure`: they are read time in
        # total and no part-level figure exists.
        evidence=(f"{touched.get('lugemine', 0)} текстов, "
                  f"{read['minutes']} мин" + material("lugemine")),
        touched=touched.get("lugemine", 0) >= CONTACT,
        next_task=_next_task(content, level, "lugemine"),
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
        next_task=_next_task(content, level, "raakimine"),
    ))
    return out


def readiness(
    level: str = "A2",
    progress: sqlite3.Connection | None = None,
    vocabulary: sqlite3.Connection | None = None,
    words: sqlite3.Connection | None = None,
    content: sqlite3.Connection | None = None,
    notion: sqlite3.Connection | None = None,
    today: date | None = None,
) -> Readiness:
    """Evidence for and against sitting `level`, with the reasons named."""
    today = today or date.today()
    decide, sitting = _target()
    grammar = _grammar(progress, level) if progress is not None else {}
    parts = (_parts(progress, level, content, notion)
             if progress is not None else [])
    vocab = _vocabulary(vocabulary, words, level)

    reasons: list[str] = []
    untouched = [p for p in parts if p.touched is False]
    if untouched:
        reasons.append(
            "Не тронутые части экзамена: "
            + ", ".join(f"{p.et} ({p.ru})" for p in untouched)
            + ". Ни одна часть не может быть нулевой."
        )
        # Name the thing to open, not the size of the shelf.
        first = next((p for p in untouched if p.next_task), None)
        if first:
            reasons.append(
                f"Начни с: {first.next_task['title']} ({first.et})."
            )
    if grammar and grammar["outstanding"]:
        reasons.append(
            f"Тем уровня {level} ещё не пройдено: "
            f"{len(grammar['outstanding'])} — "
            + ", ".join(grammar["outstanding"][:5])
        )
    if grammar and not grammar["checkpoint_passed"]:
        reasons.append(f"Контрольная работа {level} не сдана.")

    # The verdict reads next to its own reasons, and those have been Russian
    # since the language rule was written down -- so the app was rendering
    # "A2 · ei ole veel" above a paragraph of Russian explaining why. The
    # verdict is a judgement about the learner, which is exactly the category
    # `CLAUDE.md` puts in Russian: this is where comprehension has to win.
    #
    # The Estonian is kept beside it rather than dropped. `tõendid toetavad`
    # is the phrase that would appear on nothing official, but the level names
    # and part names around it are exam vocabulary, and a verdict that reads as
    # a foreign island in its own card is worse than one that teaches its own
    # two words.
    if not grammar:
        verdict = "неизвестно"
    elif not reasons:
        verdict = "данные говорят «да»"
    elif untouched or len(reasons) > 1:
        verdict = "ещё нет"
    else:
        verdict = "почти"

    return Readiness(
        level=level,
        parts=parts,
        grammar=grammar,
        vocabulary=vocab,
        verdict=verdict,
        reasons=reasons,
        days_to_decide=(decide - today).days if decide else None,
        days_to_sitting=(sitting - today).days if sitting else None,
    )
