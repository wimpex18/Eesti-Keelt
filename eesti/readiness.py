"""Should you sit the exam? An answer built only from evidence that exists.

The sitting is the learner's own choice (`exam.set_goal`), so the countdown
appears once one is picked and says so until then. HARNO runs quarterly and
closes registration about five weeks ahead.

- **No prediction.** Nothing here can calibrate a pass probability, so the
  verdict reports what the evidence shows and what is missing.
- **Four parts, never one total.** The pass rule is ≥60 % overall and no part
  at zero, so an untouched part is called out however strong the rest is.
- **Rääkimine is not judged.** The exam is paired and dialogic; the app offers
  preparation, not assessment, and says so.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date



def _count(n: int, one: str, few: str, many: str) -> str:
    """A count with its Russian noun in the right form: 1 текст, 2 текста, 5 текстов."""
    if n % 10 == 1 and n % 100 != 11:
        form = one
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        form = few
    else:
        form = many
    return f"{n} {form}"


def _target(progress: sqlite3.Connection | None) -> tuple[date | None, date | None]:
    """`(registration_closes, sitting)` of the chosen goal, or `(None, None)`.

    `registration_closes` is HARNO's hard deadline, not a personal checkpoint.
    """
    from .exam import goal

    if progress is None:
        return (None, None)
    chosen = goal(progress)
    return (chosen.registration_closes, chosen.sitting) if chosen else (None, None)

#: The four parts (A2: 20 points each, B1: 25), in the order the exam runs them.
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
    #: The chosen sitting, as `(registration_closes, sitting)`; both None until
    #: one is picked (`exam.set_goal`).
    target: tuple[date | None, date | None] = (None, None)

    @property
    def countdown(self) -> str:
        """The one number that motivates without lying.

        A streak rewards attendance and collapses the week someone falls ill.
        A date does not move, does not judge, and does not reset — it is simply
        true, and it is the fact that actually applies pressure.
        """
        if self.days_to_decide is None:
            # No session chosen: say so rather than count down to nothing.
            return "экзамен ещё не выбран"
        if self.days_to_decide > 0:
            return f"до регистрации {self.days_to_decide} дн."
        if self.days_to_sitting > 0:
            return f"до экзамена {self.days_to_sitting} дн."
        return "дата прошла"

    def _deadline(self) -> dict | None:
        """The registration date, or a note while no session is chosen."""
        decide, sitting = self.target
        if decide is None or sitting is None:
            return {
                "registration": None,
                "sitting": None,
                "note": (
                    "Сессия пока не выбрана. Выбери её в «Eksam» — и здесь "
                    "появится обратный отсчёт и напоминание о регистрации."
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
            # Registration closes weeks before a sitting; None while no session is chosen
            # (see `_deadline`).
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
        # Topic names, not ids: the learner studies **ühildumine**, not `uhildumine`.
        # `reasons` puts this list straight onto the readiness screen.
        "outstanding": [t.et for t in left],
        # Kept as well, for a caller that needs identity rather than a label.
        "outstanding_ids": [t.id for t in left],
        "checkpoint_passed": level in passed_levels(progress),
    }


def _vocabulary(vocabulary, words, level: str) -> dict:
    """Words known at this level, against what the level contains.

    A count, not a verdict. Known means `KNOWN` or `WELL_KNOWN` in
    `vocab_status.status`; `IGNORED` is excluded (words the learner chose to
    skip). Scoped to the level because the line reads "N из M слов уровня"; the
    intersection happens here because lemmas and levels live in different
    databases. A failed read returns `measured: False`, never a zero.
    """
    from .vocab import IGNORED, SETTLED

    if vocabulary is None or words is None:
        return {"known": 0, "level_words": 0, "measured": False}
    at_level = {
        row[0] for row in words.execute(
            "SELECT word FROM words WHERE proficiency = ?", (level,))
    }
    settled = sorted(SETTLED - {IGNORED})
    try:
        known = {
            row[0] for row in vocabulary.execute(
                "SELECT lemma FROM vocab_status WHERE status IN "
                f"({','.join('?' * len(settled))})", settled)
        }
    except sqlite3.Error:
        # Nothing was counted; "0 known" would be a claim about the learner.
        return {"known": 0, "level_words": len(at_level), "measured": False}
    return {"known": len(known & at_level), "level_words": len(at_level),
            "measured": True}


def _official(content, level: str) -> dict[str, int]:
    """How many official task pointers exist per exam part at this level."""
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

    Tasks only (not workbooks), first by title so HARNO's own numbering decides.
    """
    if content is None:
        return None
    try:
        row = content.execute(
            """SELECT i.id, i.title, i.meta, i.level, i.source_id,
                      LENGTH(TRIM(COALESCE(i.body, ''))) AS body_length
               FROM items i
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
    from .library import _file_here, exam_stored_path

    local = bool(row["body_length"]) or _file_here(exam_stored_path(
        meta, row["level"], row["source_id"]))
    return {"id": row["id"], "title": row["title"],
            "url": meta.get("url"), "local": local}


def _speaking_evidence() -> str:
    """What the log says about speaking practice, in Russian. Counts and pace —
    never a judgement: the exam is paired and examiner-marked."""
    from . import evidence
    from .learner import speaking_practice

    try:
        with evidence.connect() as log:
            got = speaking_practice(log)
    except Exception:  # noqa: BLE001 - no log is "nothing recorded", not an error
        return "не измеряется"
    if not (got["answers"] or got["read_alouds"]):
        return "не измеряется"
    bits = []
    if got["answers"]:
        bits.append(_count(got["answers"], "ответ", "ответа", "ответов"))
    if got["read_alouds"]:
        bits.append(_count(got["read_alouds"], "чтение вслух", "чтения вслух",
                           "чтений вслух"))
    if got["median_wpm"]:
        bits.append(f"темп ≈ {round(got['median_wpm'])} слов/мин")
    if got["doubtful"]:
        bits.append(f"{got['doubtful']} раз распознано плохо")
    return "за 90 дней: " + ", ".join(bits)


def _parts(progress: sqlite3.Connection, level: str,
           content=None, notion=None) -> list[Part]:
    from .library import exposure

    out: list[Part] = []
    read = exposure(progress)
    official = _official(content, level)

    # Sections sat on the exam's own clock (`eesti/mock.py`): the strongest
    # evidence a part has, so it is named in every part's line.
    from .mock import counts as mock_counts

    sat = mock_counts(progress, level)

    def mock(part: str) -> str:
        n = sat.get(part, 0)
        return f" · {_count(n, 'проба', 'пробы', 'проб')} на время" if n else ""

    # Opened items per exam part: the no-part-may-be-zero rule is per part.
    from .library import parts_touched

    touched = parts_touched(progress, content) if content is not None else {}

    def material(skill: str) -> str:
        n = official.get(skill, 0)
        return f" · {n} офиц. заданий" if n else ""

    # Writing: corrections queued for the error log are its durable trace. Queued
    # and sent are counted separately — only sent rows are in the Vead database.
    # The connection is passed in so callers and tests control which queue is read.
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
        evidence=writing + material("kirjutamine") + mock("kirjutamine"),
        touched=(queued >= CONTACT or sat.get("kirjutamine", 0) > 0) if
                (queued or sat.get("kirjutamine")) else False,
        note="На экзамене четыре задания по письму.",
        next_task=_next_task(content, level, "kirjutamine"),
    ))
    # Listening counts opened tasks and dictations separately: a dictation is scored
    # evidence, an opened task is only contact.
    try:
        from .dictation import stats as dictation_stats

        heard = dictation_stats(progress)
    except sqlite3.Error:
        heard = {"attempts": 0, "passed": 0, "accuracy": None}

    opened = touched.get("kuulamine", 0)
    evidence = "открыто: " + _count(opened, "задание", "задания", "заданий")
    if heard["attempts"]:
        evidence += f" · {heard['passed']}/{heard['attempts']} диктантов"
        if heard["accuracy"] is not None:
            evidence += f", слов расслышано {heard['accuracy']:.0%}"
    out.append(Part(
        "kuulamine", "Kuulamine", "аудирование",
        evidence=evidence + material("kuulamine") + mock("kuulamine"),
        touched=(opened >= CONTACT or heard["attempts"] >= CONTACT
                 or sat.get("kuulamine", 0) > 0),
        next_task=_next_task(content, level, "kuulamine"),
    ))
    out.append(Part(
        "lugemine", "Lugemine", "чтение",
        # Reading is counted per part; minutes come from total `exposure` because no
        # per-part figure exists.
        evidence=(_count(touched.get("lugemine", 0), "текст", "текста", "текстов")
                  + ", " + _count(round(read["minutes"]), "минута", "минуты", "минут")
                  + material("lugemine") + mock("lugemine")),
        touched=(touched.get("lugemine", 0) >= CONTACT
                 or sat.get("lugemine", 0) > 0),
        next_task=_next_task(content, level, "lugemine"),
    ))
    out.append(Part(
        "raakimine", "Rääkimine", "говорение",
        evidence=_speaking_evidence() + material("raakimine") + mock("raakimine"),
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
    decide, sitting = _target(progress)
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

    # The verdict is a judgement about the learner, so it is Russian; the Estonian
    # level and part names stay beside it as exam vocabulary.
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
        target=(decide, sitting),
        grammar=grammar,
        vocabulary=vocab,
        verdict=verdict,
        reasons=reasons,
        days_to_decide=(decide - today).days if decide else None,
        days_to_sitting=(sitting - today).days if sitting else None,
    )
