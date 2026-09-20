"""A timed mock of one exam part, built only from what code can grade.

The exam's own tasks are HARNO's, and reading comprehension questions cannot be
written without inventing them, so a mock here is **not** a copy of the paper.
It is the exam's clock and shape over the app's own material, and each section
says plainly what it is:

| Part | The mock's task | Graded |
|---|---|---|
| `lugemine` | gap-fill in real corpus sentences | code |
| `kuulamine` | dictation of corpus sentences | code, word by word |
| `kirjutamine` | HARNO's own task shape and word minimum | word count by code; the writing check explains the rest |
| `raakimine` | the paired-exam question bank, recorded | not scored — the exam is paired |

Each finished section records an `exam-section` event, which readiness counts.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from .exam import SPECS

#: How many gradable tasks a section asks for. Short enough to sit in one go.
TASKS = {"lugemine": 8, "kuulamine": 5, "kirjutamine": 1, "raakimine": 2}

#: What the mock is, in Russian, per part: the learner must not read a gap-fill
#: as "this is what the reading exam looks like".
NOTE = {
    "lugemine": ("На экзамене это вопросы к тексту. Здесь — пропуски в "
                 "настоящих предложениях из корпуса: проверяются формы и "
                 "понимание фразы, а не экзаменационные вопросы."),
    "kuulamine": ("На экзамене это записи с вопросами. Здесь — диктант "
                  "(etteütlus) по корпусу: слышишь и записываешь."),
    "kirjutamine": ("Задание в форме экзамена: тип текста и минимум слов. "
                    "Считаются слова; грамматику разбирает проверка письма."),
    "raakimine": ("Экзамен сдаётся в паре, поэтому оценки здесь нет. Запиши "
                  "ответ и послушай себя: засчитывается сам факт практики."),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS exam_sections (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    level   TEXT NOT NULL,
    part    TEXT NOT NULL,
    seconds REAL NOT NULL,
    asked   INTEGER NOT NULL,
    correct INTEGER,               -- NULL where code does not grade the part
    at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_exam_sections ON exam_sections(level, part, id);
"""


@dataclass(frozen=True)
class Section:
    level: str
    part: str
    minutes: int
    #: `cloze` | `dictation` | `writing` | `speaking`: how the page renders it.
    kind: str
    tasks: list = field(default_factory=list)
    graded: bool = True
    note: str = ""

    @property
    def et(self) -> str:
        """The part's Estonian name, as the exam says it."""
        return SPECS[self.level].part(self.part).et

    def to_dict(self) -> dict:
        return {"level": self.level, "part": self.part, "et": self.et,
                "minutes": self.minutes, "kind": self.kind, "tasks": self.tasks,
                "graded": self.graded, "note": self.note}


def build(level: str, part: str, *, seed: int, content: sqlite3.Connection | None,
          words: sqlite3.Connection | None = None,
          vocabulary: sqlite3.Connection | None = None) -> Section:
    """One section, seeded so it can be rebuilt exactly (`eesti/itemref.py`)."""
    spec = SPECS[level]
    minutes = spec.part(part).minutes   # ValueError for an unknown part
    if part == "lugemine":
        return _reading(level, minutes, seed, content, words)
    if part == "kuulamine":
        return _listening(level, minutes, seed, content, words, vocabulary)
    if part == "kirjutamine":
        return _writing(level, minutes)
    if part == "raakimine":
        return _speaking(level, minutes, seed)
    raise ValueError(f"no such exam part: {part!r}")


def _reading(level: str, minutes: int, seed: int, content, words) -> Section:
    from .cloze import case_clozes, sentences

    pool = sentences(content) if content is not None else []
    items = case_clozes(pool, words=words, count=TASKS["lugemine"], seed=seed) if pool else []
    return Section(level, "lugemine", minutes, "cloze", list(items),
                   note=NOTE["lugemine"])


def _listening(level: str, minutes: int, seed: int, content, words, vocabulary) -> Section:
    from .dictation import choose

    passages = choose(content, vocabulary=vocabulary, words=words,
                      count=TASKS["kuulamine"], seed=seed) if content is not None else []
    return Section(level, "kuulamine", minutes, "dictation",
                   [p.to_dict() for p in passages], note=NOTE["kuulamine"])


def _writing(level: str, minutes: int) -> Section:
    part = SPECS[level].part("kirjutamine")
    return Section(level, "kirjutamine", minutes, "writing",
                   [{"about": part.about, "min_words": MIN_WORDS[level]}],
                   note=NOTE["kirjutamine"])


#: HARNO's own minimum for the longer writing task, by level.
MIN_WORDS = {"A2": 30, "B1": 100}


def _speaking(level: str, minutes: int, seed: int) -> Section:
    import random

    from .speaking import bank

    questions = bank()
    rng = random.Random(seed)
    picked = rng.sample(questions, min(TASKS["raakimine"], len(questions)))
    return Section(level, "raakimine", minutes, "speaking",
                   [{"question": q.question, "hint_ru": q.hint_ru, "topic": q.topic}
                    for q in picked],
                   graded=False, note=NOTE["raakimine"])


def record(progress: sqlite3.Connection, level: str, part: str, seconds: float,
           asked: int, correct: int | None) -> dict:
    """Record a finished section. `correct` is None where code does not grade it."""
    from . import evidence

    payload = {"level": level, "part": part, "seconds": round(float(seconds), 1),
               "asked": asked, "correct": correct}
    ev = evidence.record("exam-section", payload)
    _record(progress, payload, ev.ts)
    return payload | {"at": ev.ts}


def _record(progress: sqlite3.Connection, p: dict, at: str) -> None:
    progress.executescript(SCHEMA)
    with progress:
        progress.execute(
            "INSERT INTO exam_sections (level, part, seconds, asked, correct, at)"
            " VALUES (?,?,?,?,?,?)",
            (p["level"], p["part"], p["seconds"], p["asked"], p["correct"], at))


def _register() -> None:
    from . import evidence

    @evidence.applies("exam-section")
    def _apply_section(stores, ev) -> None:
        _record(stores["progress"], ev.payload, ev.ts)


_register()


def history(progress: sqlite3.Connection, level: str | None = None) -> list[dict]:
    """Sections sat, newest first."""
    progress.executescript(SCHEMA)
    sql = "SELECT * FROM exam_sections"
    params: list = []
    if level:
        sql += " WHERE level = ?"
        params.append(level)
    sql += " ORDER BY id DESC LIMIT 50"
    return [dict(r) for r in progress.execute(sql, params)]


def counts(progress: sqlite3.Connection, level: str) -> dict[str, int]:
    """How many sections of each part were sat at this level."""
    progress.executescript(SCHEMA)
    return {r[0]: r[1] for r in progress.execute(
        "SELECT part, COUNT(*) FROM exam_sections WHERE level = ? GROUP BY part",
        (level,))}
