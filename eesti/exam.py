"""The exam: its shape, its sittings, and which one is being prepared for.

Facts from HARNO's own pages (`SOURCE`, checked `VERIFIED`), kept as data so the
app never invents them:

- **A2** four parts of 20 points, **B1** four parts of 25;
- pass at **≥60 %** of the total **and no part at zero** — which is why
  readiness reports the parts separately and never one number;
- speaking is **paired**: two candidates and an examiner, two assessors.

A sitting is the learner's choice, not a constant: `set_goal` records a
`goal-set` event and the projection is one row in `progress.db`. With no goal
there is no countdown.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import date

#: Where the numbers come from, and when they were last checked against it.
SOURCE = "https://harno.ee/eesti-keele-tasemeeksamid"
VERIFIED = date(2026, 9, 19)

#: Pass rule, both levels: 60 % of the total, and no part at zero.
PASS_SHARE = 0.6


@dataclass(frozen=True)
class Part:
    id: str
    et: str
    ru: str
    minutes: int
    points: int
    #: What the part asks of the candidate, in Russian.
    about: str
    note: str = ""


@dataclass(frozen=True)
class Spec:
    level: str
    parts: tuple[Part, ...]

    @property
    def total(self) -> int:
        return sum(p.points for p in self.parts)

    @property
    def pass_mark(self) -> int:
        """Points needed overall, rounded up: 60 % of the total."""
        return -(-self.total * 6 // 10)

    def part(self, part_id: str) -> Part:
        return next(p for p in self.parts if p.id == part_id)

    def to_dict(self) -> dict:
        return {"level": self.level, "parts": [asdict(p) for p in self.parts],
                "total": self.total, "pass_mark": self.pass_mark,
                "pass_share": PASS_SHARE, "no_part_at_zero": True,
                "source": SOURCE, "verified": VERIFIED.isoformat()}


SPECS: dict[str, Spec] = {
    "A2": Spec("A2", (
        Part("kirjutamine", "Kirjutamine", "письмо", 30, 20,
             "Два задания: данные по визитке (25+ слов) и сообщение, "
             "приглашение или описание (30+ слов)."),
        Part("kuulamine", "Kuulamine", "аудирование", 30, 20,
             "Короткие записи с вопросами."),
        Part("lugemine", "Lugemine", "чтение", 50, 20,
             "Тексты с вопросами, подбор и заполнение пропусков."),
        Part("raakimine", "Rääkimine", "говорение", 15, 20,
             "В паре: описание картинки, ответы партнёру и диалог по карточкам.",
             note="Оценивают два экзаменатора; в одиночку это не измерить."),
    )),
    "B1": Spec("B1", (
        Part("kirjutamine", "Kirjutamine", "письмо", 30, 25,
             "Анкета или сообщение (около 50 слов), либо рассказ или личное "
             "письмо (около 100 слов).",
             note="HARNO называет 30 или 35 минут; берём меньшее."),
        Part("kuulamine", "Kuulamine", "аудирование", 30, 25,
             "Записи с вопросами.", note="HARNO: 30–35 минут."),
        Part("lugemine", "Lugemine", "чтение", 50, 25,
             "Подбор к ситуации, выбор ответа, пропуски и вставка предложений."),
        Part("raakimine", "Rääkimine", "говорение", 15, 25,
             "В паре: обсуждение анкеты, разговор до общего решения и ролевая "
             "игра с обменом информацией.",
             note="Оценивают два экзаменатора; в одиночку это не измерить."),
    )),
}


@dataclass(frozen=True)
class Session:
    """A sitting HARNO has published, and the day registration for it closes."""

    level: str
    sitting: date
    registration_closes: date

    def to_dict(self) -> dict:
        return {"level": self.level, "sitting": self.sitting.isoformat(),
                "registration_closes": self.registration_closes.isoformat()}


#: Published sittings. Registration is in EIS (`eis.ekk.edu.ee`); the exam is
#: free and results come within 40 days.
SESSIONS: tuple[Session, ...] = (
    Session("A2", date(2026, 11, 7), date(2026, 10, 1)),
    Session("B1", date(2026, 11, 8), date(2026, 10, 1)),
)

#: What is known about the year after the published ones, in Russian.
NEXT_YEAR = ("Даты на 2027 год ещё не опубликованы. Регистрация на 2027 год "
             "открывается 1 января 2027 года (harno.ee).")


def upcoming(level: str | None = None, today: date | None = None) -> list[Session]:
    """Sittings still ahead, soonest first."""
    today = today or date.today()
    return sorted(
        (s for s in SESSIONS
         if s.sitting >= today and (level is None or s.level == level)),
        key=lambda s: s.sitting)


SCHEMA = """
CREATE TABLE IF NOT EXISTS goal (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    level               TEXT NOT NULL,
    sitting             TEXT,
    registration_closes TEXT,
    set_at              TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Goal:
    level: str
    sitting: date | None
    registration_closes: date | None
    set_at: str

    def to_dict(self) -> dict:
        return {"level": self.level,
                "sitting": self.sitting.isoformat() if self.sitting else None,
                "registration_closes": (self.registration_closes.isoformat()
                                        if self.registration_closes else None),
                "set_at": self.set_at}


def goal(progress: sqlite3.Connection) -> Goal | None:
    """The sitting being prepared for, or None while none is chosen."""
    progress.executescript(SCHEMA)
    row = progress.execute("SELECT * FROM goal WHERE id = 1").fetchone()
    if row is None:
        return None
    return Goal(
        level=row["level"],
        sitting=date.fromisoformat(row["sitting"]) if row["sitting"] else None,
        registration_closes=(date.fromisoformat(row["registration_closes"])
                             if row["registration_closes"] else None),
        set_at=row["set_at"])


def set_goal(progress: sqlite3.Connection, level: str, sitting: date | None) -> Goal:
    """Choose a sitting (or, with `sitting=None`, a level with no date yet).

    A sitting not in `SESSIONS` is accepted: HARNO publishes dates later than
    this app is rebuilt, and refusing the learner's own date would be worse than
    trusting it.
    """
    from . import evidence

    if level not in SPECS:
        raise ValueError(f"level must be one of {sorted(SPECS)}")
    closes = next((s.registration_closes for s in SESSIONS
                   if s.level == level and s.sitting == sitting), None)
    payload = {"level": level,
               "sitting": sitting.isoformat() if sitting else None,
               "registration_closes": closes.isoformat() if closes else None}
    ev = evidence.record("goal-set", payload)
    _set(progress, payload, ev.ts)
    return goal(progress)


def _set(progress: sqlite3.Connection, p: dict, at: str) -> None:
    progress.executescript(SCHEMA)
    with progress:
        progress.execute(
            "INSERT INTO goal (id, level, sitting, registration_closes, set_at)"
            " VALUES (1,?,?,?,?)"
            " ON CONFLICT(id) DO UPDATE SET level = excluded.level,"
            "   sitting = excluded.sitting,"
            "   registration_closes = excluded.registration_closes,"
            "   set_at = excluded.set_at",
            (p["level"], p["sitting"], p["registration_closes"], at))


def _register() -> None:
    from . import evidence

    @evidence.applies("goal-set")
    def _apply_goal(stores, ev) -> None:
        _set(stores["progress"], ev.payload, ev.ts)


_register()


def calendar(g: Goal) -> str:
    """The sitting and its registration deadline as an `.ics` file."""
    def ev(uid: str, on: date, summary: str, body: str) -> str:
        return ("BEGIN:VEVENT\r\n"
                f"UID:{uid}@eesti-keelt\r\n"
                f"DTSTAMP:{date.today():%Y%m%d}T000000Z\r\n"
                f"DTSTART;VALUE=DATE:{on:%Y%m%d}\r\n"
                f"SUMMARY:{summary}\r\n"
                f"DESCRIPTION:{body}\r\n"
                "END:VEVENT\r\n")

    out = ["BEGIN:VCALENDAR\r\n", "VERSION:2.0\r\n",
           "PRODID:-//eesti-keelt//exam//ET\r\n"]
    if g.registration_closes:
        out.append(ev(f"reg-{g.level}-{g.registration_closes}", g.registration_closes,
                      f"Registreerimine lõpeb — {g.level} tasemeeksam",
                      "Последний день регистрации в EIS (eis.ekk.edu.ee)."))
    if g.sitting:
        out.append(ev(f"exam-{g.level}-{g.sitting}", g.sitting,
                      f"{g.level} tasemeeksam",
                      f"Экзамен {g.level}. Результаты — в течение 40 дней."))
    out.append("END:VCALENDAR\r\n")
    return "".join(out)
