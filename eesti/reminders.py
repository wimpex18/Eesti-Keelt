"""What is worth interrupting a day for, and what is not.

A reminder is not a nudge to open the app: it is one of four facts the learner
asked to be told, each decided by code from the evidence, never by a model:

| Reminder | When |
|---|---|
| `kordamine` | at least `DUE_ENOUGH` cards are due |
| `plaan`     | nothing studied today, and the learner's chosen hour has passed |
| `registreerimine` | `REGISTRATION_WARNINGS` days before registration closes for the chosen sitting |
| `tagasi`    | nothing studied for `IDLE_DAYS` days — once, not daily |

**Counts only.** A payload carries a number and a fixed phrase; never a
sentence the learner wrote, a word they missed, or a transcript
(`eesti/logs.py` keeps the same rule for logs). That is what makes it safe for
the notification to travel through Apple's and Google's push services.

Quiet hours and the opt-in are learner state, recorded in the evidence log
(`reminder-settings`), so they survive a cold start like everything else. The
Worker's cron asks `/api/reminders`; nothing here sends anything.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone

#: Fewer than this is not worth a notification: the queue will still be there.
DUE_ENOUGH = 10

#: Days of silence before the app says anything about it, and it says it once.
IDLE_DAYS = 3

#: Registration closes at 23:59; these are the warnings before it.
REGISTRATION_WARNINGS = (14, 3)

#: Europe/Tallinn, where the exam is sat and the learner lives. The offset is
#: EET/EEST; `zoneinfo` resolves the day's rule.
ZONE = "Europe/Tallinn"

DEFAULTS = {
    # Off until the learner turns it on, in the interface, with the browser's
    # own permission prompt in front of it.
    "on": False,
    #: The hour after which "nothing studied today" is worth saying.
    "hour": 19,
    #: No notification between these hours, whatever is due.
    "quiet_from": 22,
    "quiet_to": 8,
}


@dataclass(frozen=True)
class Reminder:
    #: Stable per reason and day, so the same fact is not sent twice.
    tag: str
    #: Estonian, like every label in the interface.
    title: str
    #: Russian, like every explanation.
    body: str
    #: Where it opens in the app.
    url: str

    def to_dict(self) -> dict:
        return asdict(self)


def _local(now: datetime | None = None) -> datetime:
    from zoneinfo import ZoneInfo

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(ZoneInfo(ZONE))


def settings(log: sqlite3.Connection) -> dict:
    """The learner's own choices, last write wins."""
    rows = log.execute(
        "SELECT payload FROM events WHERE type = 'reminder-settings'"
        " ORDER BY seq DESC LIMIT 1").fetchone()
    chosen = json.loads(rows["payload"]) if rows else {}
    return {**DEFAULTS, **{k: v for k, v in chosen.items() if k in DEFAULTS}}


def quiet(prefs: dict, now: datetime | None = None) -> bool:
    """Whether the hour is one the learner asked to be left alone in."""
    hour = _local(now).hour
    start, end = prefs["quiet_from"], prefs["quiet_to"]
    return hour >= start or hour < end if start > end else start <= hour < end


def _count(n: int, one: str, few: str, many: str) -> str:
    tail = n % 100
    if 11 <= tail <= 14:
        return f"{n} {many}"
    return f"{n} {one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many}"


#: Event types that mean the learner actually studied, as opposed to opened the
#: app. `exposure` counts: reading a text is study.
STUDIED = ("attempt", "review", "dictation", "writing", "speech", "exposure",
           "comprehension", "exam-section")


def last_studied(log: sqlite3.Connection) -> date | None:
    """The day of the last thing the learner did, in their own time zone."""
    marks = ",".join("?" * len(STUDIED))
    row = log.execute(
        f"SELECT ts FROM events WHERE type IN ({marks}) ORDER BY seq DESC LIMIT 1",  # noqa: S608
        STUDIED).fetchone()
    if row is None:
        return None
    at = datetime.fromisoformat(row["ts"])
    return _local(at if at.tzinfo else at.replace(tzinfo=timezone.utc)).date()


def due(log: sqlite3.Connection, review: sqlite3.Connection,
        progress: sqlite3.Connection, now: datetime | None = None) -> list[Reminder]:
    """Everything worth saying at this moment. Empty is the common answer."""
    prefs = settings(log)
    if not prefs["on"] or quiet(prefs, now):
        return []

    here = _local(now)
    today = here.date()
    studied = last_studied(log)
    out: list[Reminder] = []

    cards = review.execute(
        "SELECT COUNT(*) FROM review_items WHERE due <= ?",
        ((now or datetime.now(timezone.utc)).isoformat(),)).fetchone()[0]
    if cards >= DUE_ENOUGH:
        out.append(Reminder(
            f"kordamine-{today}", "Kordamine",
            f"К повторению {_count(cards, 'карточка', 'карточки', 'карточек')}. "
            "Повторить вовремя дешевле, чем выучить заново.",
            "/#review"))

    if studied != today and here.hour >= prefs["hour"]:
        out.append(Reminder(
            f"plaan-{today}", "Täna",
            "Сегодня ещё ничего не сделано. План на сегодня уже готов.",
            "/#path"))

    if studied is not None and (today - studied).days >= IDLE_DAYS:
        # Once per stretch of silence, not once a day: the tag is the day the
        # learner stopped, so a longer gap does not send a second one.
        out.append(Reminder(
            f"tagasi-{studied}", "Eesti keel",
            f"Перерыв {_count((today - studied).days, 'день', 'дня', 'дней')}. "
            "Даже десять минут удержат карточки.",
            "/#path"))

    out.extend(_registration(progress, today))
    return out


def _registration(progress: sqlite3.Connection, today: date) -> list[Reminder]:
    """The deadline that cannot be repeated: registration closes once."""
    from .exam import goal

    chosen = goal(progress)
    if chosen is None or not chosen.registration_closes:
        return []
    left = (chosen.registration_closes - today).days
    if left not in REGISTRATION_WARNINGS:
        return []
    return [Reminder(
        f"registreerimine-{chosen.registration_closes}-{left}", "Registreerimine",
        f"Регистрация на экзамен ({chosen.level}) закрывается через "
        f"{_count(left, 'день', 'дня', 'дней')} — {chosen.registration_closes:%d.%m}. "
        "Регистрация идёт в EIS.",
        "/#exam")]


def choose(**changes) -> dict:
    """Record the learner's choices, and return what is in force now."""
    from . import evidence

    kept = {k: v for k, v in changes.items() if k in DEFAULTS}
    for name in ("hour", "quiet_from", "quiet_to"):
        if name in kept:
            kept[name] = max(0, min(23, int(kept[name])))
    if "on" in kept:
        kept["on"] = bool(kept["on"])
    with evidence.connect() as log:
        now = {**settings(log), **kept}
    evidence.record("reminder-settings", now)
    return now


def next_check(prefs: dict, now: datetime | None = None) -> datetime:
    """When the cron's next look could matter — for documenting the schedule."""
    here = _local(now)
    wake = here.replace(hour=prefs["hour"], minute=0, second=0, microsecond=0)
    return wake if wake > here else datetime.combine(
        here.date() + timedelta(days=1), time(prefs["hour"]), tzinfo=here.tzinfo)
