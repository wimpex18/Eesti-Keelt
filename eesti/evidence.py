"""The learner's evidence log: every learner-state change, as an append-only event.

The log is the source of truth. `progress.db`, `review.db`, `vocab.db` and
`notion.db` hold *projections* of it: each can be thrown away and rebuilt by
replaying the log (`rebuild`). The Worker keeps the durable copy of the log in the
learner's Durable Object and pulls new events after every request
(`/api/events`); a fresh instance gets the whole log back (`/api/events/import`).

How a change is recorded:

- a domain function (`progress.record`, `review.grade`, ...) calls `record()` to
  append the event, then applies it to the connection it was given;
- `rebuild()` calls the same apply functions, registered with `@applies`, over
  the whole log;
- anything an apply function needs from time or chance travels in the event
  (`ts`, card ids, the seeded card state), so a replay reproduces the rows.

Rows written before the log existed enter it once, as `legacy-row` events with ids
derived from their content, followed by the `backfill` marker (`backfill`).
Linguistic data, dictionary caches and the provider breaker are not learner
evidence and never enter the log.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

#: Envelope version. Bump when a payload changes shape, and teach `apply` the old one.
VERSION = 1

#: The event that says the pre-log rows are in the log. Fixed id, so a second
#: backfill of the same state is a no-op wherever it happens.
BACKFILL_ID = "backfill"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq     INTEGER PRIMARY KEY AUTOINCREMENT,
    id      TEXT NOT NULL UNIQUE,
    v       INTEGER NOT NULL,
    type    TEXT NOT NULL,
    ts      TEXT NOT NULL,
    learner TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""

#: Projection tables per learner database. Everything else in those files (the
#: breaker, repairs, the dictionary cache) is operational and survives a rebuild.
PROJECTIONS: dict[str, tuple[str, ...]] = {
    "progress": ("attempts", "topic_state", "checkpoints", "dictation", "exposure",
                 "goal", "exam_sections"),
    "review": ("review_items",),
    "vocab": ("vocab_status",),
    "notion": ("notion_queue",),
}


@dataclass(frozen=True)
class Event:
    id: str
    type: str
    ts: str
    payload: dict
    v: int = VERSION
    learner: str = "owner"
    seq: int | None = field(default=None, compare=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "ts": self.ts, "v": self.v,
                "learner": self.learner, "payload": self.payload}

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(id=str(d["id"]), type=str(d["type"]), ts=str(d["ts"]),
                   payload=dict(d.get("payload") or {}), v=int(d.get("v", VERSION)),
                   learner=str(d.get("learner") or "owner"), seq=d.get("seq"))

    @property
    def at(self) -> datetime:
        return datetime.fromisoformat(self.ts)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def learner() -> str:
    return os.environ.get("EESTI_LEARNER", "owner")


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    from . import config

    target = Path(path or config.EVENTS_DB)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _row(r: sqlite3.Row) -> Event:
    return Event(id=r["id"], type=r["type"], ts=r["ts"], v=r["v"],
                 learner=r["learner"], payload=json.loads(r["payload"]), seq=r["seq"])


def _insert(conn: sqlite3.Connection, ev: Event) -> bool:
    cur = conn.execute(
        "INSERT OR IGNORE INTO events (id, v, type, ts, learner, payload)"
        " VALUES (?,?,?,?,?,?)",
        (ev.id, ev.v, ev.type, ev.ts, ev.learner,
         json.dumps(ev.payload, ensure_ascii=False, sort_keys=True)),
    )
    return cur.rowcount > 0


def has(conn: sqlite3.Connection, event_id: str) -> bool:
    """Whether this event is already in the log — the check an answer given
    offline needs, so replaying the queue records it once."""
    return conn.execute(
        "SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone() is not None


def has_backfill(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM events WHERE id = ?", (BACKFILL_ID,)).fetchone() is not None


class NotRestored(RuntimeError):
    """A write reached an instance the Worker has not restored yet."""


def restored_by_worker() -> bool:
    """True on the deployment (`EESTI_WORKER_RESTORES`, set in the Dockerfile): only
    the Worker's restore may start the log there, never a write."""
    return os.environ.get("EESTI_WORKER_RESTORES") == "1"


def record(type_: str, payload: dict, *, ts: str | None = None,
           id_: str | None = None) -> Event:
    """Append one event. The caller applies it to its own connection.

    Before the first event of a database that predates the log, the rows already
    there are backfilled, so the log never starts in the middle of a history.
    On the deployment that is the Worker's restore's job (`settle`): a write that
    arrives first is refused, since backfilling an empty instance would mark an
    empty history as the whole of it.
    """
    ev = Event(id=id_ or str(uuid.uuid7()), type=type_, ts=ts or now(),
               payload=payload, learner=learner())
    with connect() as conn:
        if not has_backfill(conn):
            if restored_by_worker():
                raise NotRestored("the evidence log has not been restored yet")
            backfill(conn)
        _insert(conn, ev)
    return ev


# --------------------------------------------------------------------------
# Applying events
# --------------------------------------------------------------------------

Apply = Callable[["Stores", Event], object]
_APPLY: dict[str, Apply] = {}


def applies(type_: str) -> Callable[[Apply], Apply]:
    """Register the function that turns one event type into projection rows."""
    def register(fn: Apply) -> Apply:
        _APPLY[type_] = fn
        return fn
    return register


class Stores:
    """The four learner databases, opened lazily from `config` by their own openers."""

    def __init__(self) -> None:
        self._open: dict[str, sqlite3.Connection] = {}

    def __getitem__(self, name: str) -> sqlite3.Connection:
        if name not in self._open:
            self._open[name] = _open(name)
        return self._open[name]

    def close(self) -> None:
        for conn in self._open.values():
            conn.close()
        self._open.clear()


def _open(name: str) -> sqlite3.Connection:
    from . import (checkpoint, config, dictation, exam, library, mock, notion,
                   progress, review, vocab)

    if name == "progress":
        conn = progress.connect(config.PROGRESS_DB)
        conn.executescript(checkpoint.SCHEMA)
        conn.executescript(exam.SCHEMA)
        conn.executescript(mock.SCHEMA)
        conn.executescript(library.SCHEMA)
        dictation.ensure(conn)
        return conn
    if name == "review":
        return review.connect(config.REVIEW_DB)
    if name == "vocab":
        return vocab.connect(config.VOCAB_DB)
    if name == "notion":
        return notion.connect(config.NOTION_DB)
    raise KeyError(name)


def _register_all() -> None:
    """Import every module that registers an apply function."""
    from . import (checkpoint, dictation, exam, library, mock,  # noqa: F401
                   notion, progress, review, vocab)


@applies("legacy-row")
def _legacy_row(stores: Stores, ev: Event) -> None:
    """A row that existed before the log, written back exactly as it was."""
    db, table, row = ev.payload["db"], ev.payload["table"], ev.payload["row"]
    if table not in PROJECTIONS.get(db, ()):
        raise ValueError(f"not a projection table: {db}.{table}")
    cols = list(row)
    conn = stores[db]
    with conn:
        conn.execute(
            f"INSERT OR REPLACE INTO {table} ({','.join(cols)})"  # noqa: S608 - names checked above
            f" VALUES ({','.join('?' * len(cols))})",
            [row[c] for c in cols],
        )


@applies("backfill")
def _backfill_marker(stores: Stores, ev: Event) -> None:
    """The marker carries no rows."""


#: Evidence with no table of its own: read from the log itself (skill balance,
#: the plan's history), so replaying them writes nothing.
LOG_ONLY = ("writing", "speech", "plan-issued", "conversation")
for _type in LOG_ONLY:
    applies(_type)(lambda stores, ev: None)


def since(conn: sqlite3.Connection, types: tuple[str, ...], after_ts: str) -> list[Event]:
    """Events of these types at or after an ISO time, oldest first."""
    marks = ",".join("?" * len(types))
    rows = conn.execute(
        f"SELECT * FROM events WHERE type IN ({marks}) AND ts >= ? ORDER BY seq",  # noqa: S608
        (*types, after_ts))
    return [_row(r) for r in rows]


def apply(stores: Stores, ev: Event) -> object:
    _register_all()
    try:
        fn = _APPLY[ev.type]
    except KeyError as exc:
        raise ValueError(f"no apply function for event type {ev.type!r}") from exc
    return fn(stores, ev)


# --------------------------------------------------------------------------
# Backfill, rebuild, export and import
# --------------------------------------------------------------------------

def backfill(conn: sqlite3.Connection) -> int:
    """Put the rows written before the log into it, once, then the marker.

    Ids are derived from the row, so two backfills of one state agree.
    """
    stores = Stores()
    added = 0
    try:
        for db, tables in PROJECTIONS.items():
            source = stores[db]
            for table in tables:
                for r in source.execute(f"SELECT * FROM {table} ORDER BY rowid"):  # noqa: S608
                    row = dict(r)
                    body = json.dumps([db, table, row], ensure_ascii=False,
                                      sort_keys=True, default=str)
                    digest = hashlib.sha256(body.encode()).hexdigest()[:24]
                    added += _insert(conn, Event(
                        id=f"v0-{digest}", type="legacy-row", ts=now(), v=0,
                        learner=learner(),
                        payload={"db": db, "table": table, "row": row}))
    finally:
        stores.close()
    _insert(conn, Event(id=BACKFILL_ID, type="backfill", ts=now(),
                        payload={"rows": added}, learner=learner()))
    conn.commit()
    return added


def events(conn: sqlite3.Connection, after: int = 0,
           limit: int | None = None) -> list[Event]:
    sql = "SELECT * FROM events WHERE seq > ? ORDER BY seq"
    params: list = [after]
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return [_row(r) for r in conn.execute(sql, params)]


def last_seq(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()[0]


def ingest(conn: sqlite3.Connection, incoming: Iterable[dict]) -> int:
    """Append events that are not already here (by id). Returns how many were new."""
    added = 0
    with conn:
        for d in incoming:
            added += _insert(conn, Event.from_dict(d))
    return added


def rebuild(conn: sqlite3.Connection | None = None) -> int:
    """Throw the projection tables away and replay the whole log into them."""
    own = conn is None
    conn = conn or connect()
    stores = Stores()
    try:
        for db, tables in PROJECTIONS.items():
            target = stores[db]
            with target:
                for table in tables:
                    target.execute(f"DELETE FROM {table}")  # noqa: S608 - fixed names
                # Ids restart as they first ran, so replayed row ids match.
                # (`sqlite_sequence` exists once an AUTOINCREMENT table had a row.)
                if target.execute("SELECT 1 FROM sqlite_master WHERE"
                                  " name = 'sqlite_sequence'").fetchone():
                    target.execute(
                        "DELETE FROM sqlite_sequence WHERE name IN (%s)"
                        % ",".join("?" * len(tables)), tables)
        n = 0
        for ev in events(conn):
            # One event this code cannot replay (a type from a newer release, after
            # a rollback) must not stop the rest: skipped, reported, kept in the log.
            try:
                apply(stores, ev)
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).warning(
                    "replay skipped event %s (%s): %s", ev.id, ev.type, exc)
                continue
            n += 1
        return n
    finally:
        stores.close()
        if own:
            conn.close()


def settle(conn: sqlite3.Connection) -> dict:
    """Make the projections agree with the log after a restore.

    With the marker in the log, the log is complete: rebuild from it. Without it,
    this is the first run on a pre-log state: backfill from the projections.
    """
    if has_backfill(conn):
        return {"rebuilt": rebuild(conn), "backfilled": 0}
    return {"rebuilt": 0, "backfilled": backfill(conn)}


def card_id(key: str) -> int:
    """A stable FSRS card id for a review item id (`Card()` would use the clock)."""
    return int(hashlib.sha256(key.encode()).hexdigest()[:12], 16)
