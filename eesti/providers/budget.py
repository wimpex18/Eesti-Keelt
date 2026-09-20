"""A day's allowance per lane, so a free tier is never burned through by accident.

The chain skips a lane whose allowance is spent, exactly as the breaker skips a
failing one, and says so in the diagnostics. Counts live beside the breaker (in
`progress.db`) because Cloud Run scales to zero and an in-memory count would
reset several times a day — which is how a 50-a-day quota becomes 200.

The caps are this project's own, set below each provider's published limit
(`eesti/licences.py` records the limit itself): what is left has to cover the
rest of the day, and a lane that answers second is worth saving.
"""

from __future__ import annotations

import sqlite3
from datetime import date

#: Calls per day, per lane. `None` means no cap this project needs to keep.
CAPS: dict[str, int | None] = {
    "llm:openrouter": 40,        # provider allows 50/day, failures included
    "llm:nvidia": 400,           # 40/min, no daily limit published
    "llm:mistral": 400,
    "llm:workers-ai": 300,       # 10 000 neurons/day, shared with speech
    "llm:local": None,           # your machine
    "tartunlp": 500,
    "tartunlp-mt": 500,
    "asr:workers-ai": 200,       # audio minutes cost neurons too
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS budget (
    day   TEXT NOT NULL,
    lane  TEXT NOT NULL,
    calls INTEGER NOT NULL,
    PRIMARY KEY (day, lane)
);
"""

_store: sqlite3.Connection | None = None
_opener = None


def bind(conn: sqlite3.Connection | None) -> None:
    """Count in this connection (tests, the CLI), or nowhere."""
    global _store, _opener
    _store, _opener = conn, None
    if conn is not None:
        conn.executescript(SCHEMA)


def bind_later(opener) -> None:
    """Count in whatever `opener()` returns, opened per call.

    Per call, not once: the app answers requests on a thread pool, and a SQLite
    connection belongs to the thread that made it.
    """
    global _store, _opener
    _store, _opener = None, opener


def _open() -> sqlite3.Connection | None:
    if _store is not None:
        return _store
    if _opener is None:
        return None
    try:
        conn = _opener()
        conn.executescript(SCHEMA)
        return conn
    except Exception:  # noqa: BLE001 - counting is a courtesy, not a need
        return None


def _use(fn, default=None):
    """Run `fn(conn)`, closing a per-call connection afterwards."""
    conn = _open()
    if conn is None:
        return default
    try:
        return fn(conn)
    except sqlite3.Error:
        return default
    finally:
        if conn is not _store:
            conn.close()


def _today() -> str:
    return date.today().isoformat()


def spent(lane: str) -> int:
    """Calls made on this lane today."""
    def read(conn: sqlite3.Connection) -> int:
        row = conn.execute("SELECT calls FROM budget WHERE day = ? AND lane = ?",
                           (_today(), lane)).fetchone()
        return row[0] if row else 0

    return _use(read, 0)


def left(lane: str) -> int | None:
    """Calls still allowed today, or None where this project sets no cap."""
    cap = CAPS.get(lane)
    return None if cap is None else max(0, cap - spent(lane))


def exhausted(lane: str) -> bool:
    remaining = left(lane)
    return remaining is not None and remaining <= 0


def spend(lane: str, calls: int = 1) -> None:
    """Count calls made. Never raises: a lost count is better than a lost answer."""
    def write(conn: sqlite3.Connection) -> None:
        with conn:
            conn.execute(
                "INSERT INTO budget (day, lane, calls) VALUES (?,?,?)"
                " ON CONFLICT(day, lane) DO UPDATE SET calls = calls + excluded.calls",
                (_today(), lane, calls))

    _use(write)


def report() -> dict[str, dict]:
    """What each capped lane has spent today, for `/api/status`."""
    return {lane: {"cap": cap, "spent": spent(lane), "left": left(lane)}
            for lane, cap in CAPS.items() if cap is not None}
