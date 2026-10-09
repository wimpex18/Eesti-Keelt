"""A timed mock of one exam part, built only from what code can grade.

The exam's own tasks are HARNO's, and reading comprehension questions cannot be
written without inventing them, so a mock here is **not** a copy of the paper.
It is the exam's clock and shape over the app's own material, and each section
says plainly what it is:

| Part | The mock's task | Graded |
|---|---|---|
| `lugemine` | gap-fill in real corpus sentences (EKI EVS's phrases outside the owner's scope) | code |
| `kuulamine` | dictation of corpus sentences (EKI EVS's phrases outside the owner's scope) | code, word by word |
| `kirjutamine` | both of HARNO's writing tasks, each in its variants (`eesti/writingtasks.py`) | by code: a checklist — length against HARNO's figure, each point the prompt asks for, a letter's frame, the deterministic checks |
| `raakimine` | the paired-exam question bank, recorded | not scored — the exam is paired |

Reading and listening also come in HARNO's own task types (`eesti/harnotasks.py`):
part `lugemine:harno` is every type the part has, `lugemine:3` one of them,
practised on its own. A HARNO-format part is reviewed item by item (answer, key,
the evidence in the text or transcript, the topic behind a miss), and each task
type with a miss is re-tested one, then three, then six days later (`retests`).

Each finished section records an `exam-section` event, which readiness counts;
a single task type practised on its own is recorded but not counted as a part.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from .config import LEVELS
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
    "kirjutamine": ("Два задания, как на экзамене, за время всей части; в "
                    "каждом выбери вариант. Задания написаны моделью (Claude Opus "
                    "5.5) по формату HARNO. Код проверяет список: длину, есть ли "
                    "каждый пункт задания, приветствие и подпись в письме, "
                    "орфографию, согласование (ühildumine) и рекцию (rektsioon). "
                    "Это не оценка экзамена."),
    "raakimine": ("Экзамен сдаётся в паре, поэтому оценки здесь нет. Запиши "
                  "ответ и послушай себя: засчитывается сам факт практики."),
}

#: The same, where the tasks are EKI EVS's example phrases (outside the owner's
#: scope the corpus is hidden). The credit is EKI's licence condition.
NOTE_EVS = {
    "lugemine": ("На экзамене это вопросы к тексту. Здесь — пропуски во "
                 "фразах-примерах из словаря EKI (eesti-vene sõnaraamat, "
                 "CC BY 4.0): проверяются формы, а не экзаменационные вопросы."),
    "kuulamine": ("На экзамене это записи с вопросами. Здесь — диктант "
                  "(etteütlus) по фразам-примерам из словаря EKI "
                  "(eesti-vene sõnaraamat, CC BY 4.0): слышишь и записываешь."),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS exam_sections (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    level   TEXT NOT NULL,
    part    TEXT NOT NULL,
    seconds REAL NOT NULL,
    asked   INTEGER NOT NULL,
    correct INTEGER,               -- NULL where code does not grade the part
    at      TEXT NOT NULL,
    detail  TEXT                   -- JSON: what that part's own grading found
);
CREATE INDEX IF NOT EXISTS idx_exam_sections ON exam_sections(level, part, id);
"""


#: What a HARNO-format part is, in Russian: the task types, not HARNO's paper.
NOTE_HARNO = ("Задания в формате HARNO: та же инструкция, тот же вид вопросов и "
              "их номера, но материал приложения, а ключ задаёт код. Время — "
              "доля времени всей части по числу вопросов.")


@dataclass(frozen=True)
class Section:
    level: str
    part: str
    minutes: int
    #: `cloze` | `dictation` | `writing` | `speaking` | `harno`: how the page renders it.
    kind: str
    tasks: list = field(default_factory=list)
    graded: bool = True
    note: str = ""
    #: `harno`: the tasks of the part, each with its questions' place in `tasks`.
    blocks: list = field(default_factory=list)
    #: `harno`: HARNO's task types this section could not build, by number.
    missing: list = field(default_factory=list)

    @property
    def et(self) -> str:
        """The part's Estonian name, as the exam says it."""
        return SPECS[self.level].part(self.part).et

    def to_dict(self) -> dict:
        out = {"level": self.level, "part": self.part, "et": self.et,
               "minutes": self.minutes, "kind": self.kind, "tasks": self.tasks,
               "graded": self.graded, "note": self.note}
        if self.kind == "harno":
            out |= {"blocks": self.blocks, "missing": self.missing}
        return out


def build(level: str, part: str, *, seed: int, content: sqlite3.Connection | None,
          words: sqlite3.Connection | None = None,
          vocabulary: sqlite3.Connection | None = None) -> Section:
    """One section, seeded so it can be rebuilt exactly (`eesti/itemref.py`).

    `part` may name HARNO's task types: `lugemine:harno` for all of the part's,
    `lugemine:3` for one (`harno`)."""
    if ":" in part:
        part, _, which = part.partition(":")
        return harno(level, part, seed=seed, content=content, words=words,
                     only=None if which == "harno" else int(which))
    spec = SPECS[level]
    minutes = spec.part(part).minutes   # ValueError for an unknown part
    if part == "lugemine":
        return _reading(level, minutes, seed, content, words)
    if part == "kuulamine":
        return _listening(level, minutes, seed, content, words, vocabulary)
    if part == "kirjutamine":
        return _writing(level, minutes, seed)
    if part == "raakimine":
        return _speaking(level, minutes, seed)
    raise ValueError(f"no such exam part: {part!r}")


def harno(level: str, part: str, *, seed: int, content: sqlite3.Connection | None,
          words: sqlite3.Connection | None, only: int | None = None) -> Section:
    """HARNO's task types for a reading or listening part (`eesti/harnotasks.py`).

    `tasks` is every question in order; each block names its type, what is read
    or heard, and where its questions start in `tasks`. `minutes` is the share of
    the part's time its questions are. An empty section means no type could be
    built, and the page falls back to the app's own section."""
    from . import harnotasks

    spec = SPECS[level]
    spec.part(part)                         # ValueError for an unknown part
    if part not in ("lugemine", "kuulamine"):
        raise ValueError(f"no HARNO task types for {part!r}")
    if only is not None:
        harnotasks.by_number(level, part, only)     # KeyError for an unknown task
    built = harnotasks.section(level, part, seed=seed, content=content, words=words,
                               only=only)
    blocks, first = [], 0
    for block in built.blocks:
        blocks.append(block.to_page(first))
        first += len(block.questions)
    return Section(level, part, built.minutes, "harno", built.questions,
                   note=NOTE_HARNO, blocks=blocks,
                   missing=[t.to_dict() for t in built.missing])


def _up_to(level: str) -> tuple[str, ...]:
    """The word levels a mock at `level` draws on: an A2 mock uses no B1 words."""
    return LEVELS[:LEVELS.index(level) + 1] if level in LEVELS else LEVELS


def _reading(level: str, minutes: int, seed: int, content, words) -> Section:
    from .cloze import case_clozes, sentences

    pool = sentences(content) if content is not None else []
    items = case_clozes(pool, words=words, count=TASKS["lugemine"], seed=seed) if pool else []
    note = NOTE["lugemine"]
    if not items and words is not None:
        # Outside the owner's scope the corpus is hidden: EKI's phrases are public.
        from .practice import public_clozes

        items = public_clozes(words, None, TASKS["lugemine"], seed, levels=_up_to(level))
        note = NOTE_EVS["lugemine"]
    return Section(level, "lugemine", minutes, "cloze", list(items), note=note)


def _listening(level: str, minutes: int, seed: int, content, words, vocabulary) -> Section:
    from .dictation import MAX_WORDS, MIN_WORDS, choose, from_phrases

    passages = choose(content, vocabulary=vocabulary, words=words,
                      count=TASKS["kuulamine"], seed=seed) if content is not None else []
    note = NOTE["kuulamine"]
    if not passages and words is not None:
        from .evs import phrases

        passages = from_phrases(phrases(words, MIN_WORDS, MAX_WORDS, _up_to(level)),
                                vocabulary=vocabulary, count=TASKS["kuulamine"],
                                seed=seed)
        note = NOTE_EVS["kuulamine"]
    return Section(level, "kuulamine", minutes, "dictation",
                   [p.to_dict() for p in passages], note=note)


def _writing(level: str, minutes: int, seed: int) -> Section:
    from .writingtasks import for_section

    return Section(level, "kirjutamine", minutes, "writing", for_section(level, seed),
                   note=NOTE["kirjutamine"])


#: Practice thresholds for a single text sent by a page cached before both tasks
#: (HARNO's A2 minimum, B1's approximate length). Not HARNO's writing scores.
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
           asked: int, correct: int | None, detail: dict | None = None) -> dict:
    """Record a finished section. `correct` is None where code does not grade it;
    `detail` is what that part's own grading found (words written, errors)."""
    from . import evidence

    payload = {"level": level, "part": part, "seconds": round(float(seconds), 1),
               "asked": asked, "correct": correct, "detail": detail or {}}
    ev = evidence.record("exam-section", payload)
    _record(progress, payload, ev.ts)
    return payload | {"at": ev.ts}


def _record(progress: sqlite3.Connection, p: dict, at: str) -> None:
    import json

    progress.executescript(SCHEMA)
    # `detail` arrived after the first sections were recorded.
    columns = {r[1] for r in progress.execute("PRAGMA table_info(exam_sections)")}
    if "detail" not in columns:
        progress.execute("ALTER TABLE exam_sections ADD COLUMN detail TEXT")
    with progress:
        progress.execute(
            "INSERT INTO exam_sections (level, part, seconds, asked, correct, at, detail)"
            " VALUES (?,?,?,?,?,?,?)",
            (p["level"], p["part"], p["seconds"], p["asked"], p["correct"], at,
             json.dumps(p.get("detail") or {}, ensure_ascii=False)))


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
    """How many sections of each part were sat at this level. A task type
    practised on its own (`detail.practice`) is not a sitting of the part."""
    progress.executescript(SCHEMA)
    return {r[0]: r[1] for r in progress.execute(
        "SELECT part, COUNT(*) FROM exam_sections WHERE level = ?"
        " AND json_extract(COALESCE(NULLIF(detail, ''), '{}'), '$.practice') IS NULL"
        " GROUP BY part", (level,))}


#: Days to the next re-test of a task type after a miss, then after each clean
#: result: ADR-0009's "re-tested one to six days later". Three clean results in
#: a row close it.
RETEST_DAYS = (1, 3, 6)


def schedule(results: list[tuple[str, bool, list[str]]]) -> tuple[str, int, list[str]] | None:
    """When a task type is next re-tested, from its results oldest first, each
    `(date, clean, topics missed)`: `(due date, clean results since the miss, the
    miss's topics)`, or None when it has no miss or the miss is closed."""
    from datetime import date, timedelta

    misses = [n for n, (_, clean, _) in enumerate(results) if not clean]
    if not misses:
        return None
    since = len(results) - 1 - misses[-1]
    if since >= len(RETEST_DAYS):
        return None
    last = date.fromisoformat(results[-1][0][:10])
    return ((last + timedelta(days=RETEST_DAYS[since])).isoformat(), since,
            results[misses[-1]][2])


def retests(progress: sqlite3.Connection, level: str) -> list[dict]:
    """The HARNO task types to re-test at this level, soonest first: every type
    with a miss in a mock or a practice, until three clean results follow it."""
    import json

    from . import harnotasks

    progress.executescript(SCHEMA)
    by_code: dict[str, list[tuple[str, bool, list[str]]]] = {}
    for row in progress.execute(
            "SELECT at, detail FROM exam_sections WHERE level = ? ORDER BY id", (level,)):
        try:
            detail = json.loads(row["detail"] or "{}")
        except ValueError:
            continue
        for block in detail.get("blocks") or []:
            by_code.setdefault(block.get("code", ""), []).append(
                (row["at"], block.get("correct") == block.get("asked"),
                 list(block.get("topics") or [])))
    out = []
    for code, results in by_code.items():
        due = schedule(results)
        if due is None or code not in harnotasks.TYPES:
            continue
        task = harnotasks.TYPES[code]
        out.append({"code": code, "part": task.part, "no": task.no, "et": task.et,
                    "due": due[0], "clean": due[1], "topics": due[2]})
    return sorted(out, key=lambda r: (r["due"], r["code"]))


def check_writing(text: str, level: str) -> dict:
    """Grade a mock's writing by what code can decide, and nothing else.

    Length against the practice threshold, and the deterministic checks the
    writing tab already merges into every answer: spelling, subject-verb
    agreement, EKK's rection list and an object in nimetav. No model here — a model's judgement of a
    text is advisory evidence, and Kirjutamine is where it explains itself.
    """
    from .providers.grammar import agreement, nominative_objects, rection, spelling

    words = len(text.split())
    found = spelling(text) + agreement(text) + rection(text) + nominative_objects(text)
    return {
        "words": words,
        "min_words": MIN_WORDS[level],
        "long_enough": words >= MIN_WORDS[level],
        "errors": len(found),
        "errors_per_100": round(len(found) / words * 100, 1) if words else 0.0,
        "findings": [c.to_dict() for c in found[:20]],
        "checked_by": "vabamorf+ekk",
    }
