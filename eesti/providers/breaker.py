"""One circuit breaker, shared by the grammar and speech provider chains.

A dead endpoint tends to stay dead for hours, so after `THRESHOLD` failures a
provider is skipped for a cooldown that doubles per further failure, up to
about a week; `reset()` forces a retry.

State is persisted (in `progress.db`, via `bind_later`), because Cloud Run
scales to zero and an in-memory breaker would pay a dead provider's timeout on
every cold start. Timestamps are wall-clock so the next process can read them.
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager

THRESHOLD = 2
COOLDOWN = 900.0  # seconds

#: Cap on the doubling: re-probe a dead provider about weekly.
MAX_COOLDOWN = 6 * 24 * 3600.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS breaker (
    name     TEXT PRIMARY KEY,
    failures INTEGER NOT NULL,
    last     REAL NOT NULL          -- wall clock: the next process reads this
);
"""

_failures: dict[str, tuple[int, float]] = {}
_store: sqlite3.Connection | None = None

#: Set by `bind_later`; each operation opens on its own request thread.
_opener = None
_loaded = False


def bind(conn: sqlite3.Connection | None) -> None:
    """Give the breaker somewhere to remember, or `None` for in-memory state (CLI,
    tests).
    """
    global _store, _loaded, _opener
    _store = conn
    _opener = None
    _loaded = False
    if conn is not None:
        conn.executescript(SCHEMA)


def bind_later(opener) -> None:
    """Open per operation, so paths resolve at call time and each thread owns
    its SQLite connection.
    """
    global _store, _loaded, _opener
    _store = None
    _loaded = False
    _opener = opener


@contextmanager
def _connection():
    """Open on the calling request thread; never cache a thread-bound handle."""
    conn = _store
    if conn is None and _opener is not None:
        try:
            conn = _opener()
            conn.executescript(SCHEMA)
        except Exception:  # noqa: BLE001 - in-memory protection survives store failure
            if conn is not None:
                conn.close()
            conn = None
    try:
        yield conn
    except sqlite3.Error:
        # In-memory protection still works when persistence is unavailable.
        pass
    finally:
        if conn is not None and conn is not _store:
            conn.close()


def _load() -> None:
    global _loaded
    if _loaded:
        return
    with _connection() as store:
        if store is None:
            return
        for row in store.execute("SELECT name, failures, last FROM breaker"):
            _failures.setdefault(row[0], (row[1], row[2]))
        _loaded = True


def cooldown(count: int) -> float:
    """How long to skip a provider that has failed `count` times running."""
    if count < THRESHOLD:
        return 0.0
    return min(COOLDOWN * (2 ** (count - THRESHOLD)), MAX_COOLDOWN)


def is_open(name: str) -> bool:
    """True when this provider should be skipped for now."""
    _load()
    count, last = _failures.get(name, (0, 0.0))
    return count >= THRESHOLD and (time.time() - last) < cooldown(count)


def record_failure(name: str) -> None:
    _load()
    count, _ = _failures.get(name, (0, 0.0))
    now = time.time()
    _failures[name] = (count + 1, now)
    with _connection() as store:
        if store is None:
            return
        try:
            store.execute(
                "INSERT INTO breaker (name, failures, last) VALUES (?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET failures = ?, last = ?",
                (name, count + 1, now, count + 1, now),
            )
            store.commit()
        except sqlite3.Error:
            pass  # a breaker that cannot write is still a working breaker


def record_success(name: str) -> None:
    _load()
    _failures.pop(name, None)
    with _connection() as store:
        if store is None:
            return
        try:
            store.execute("DELETE FROM breaker WHERE name = ?", (name,))
            store.commit()
        except sqlite3.Error:
            pass


def reset() -> None:
    """Clear all breaker state — for tests, and for an explicit 'retry now'."""
    global _loaded
    _failures.clear()
    _loaded = True          # nothing to load; the caller means "try again now"
    with _connection() as store:
        if store is None:
            return
        try:
            store.execute("DELETE FROM breaker")
            store.commit()
        except sqlite3.Error:
            pass


def state() -> dict[str, dict]:
    """What is currently tripped, for the UI and for `cli keys`."""
    _load()
    now = time.time()
    return {
        name: {
            "failures": count,
            "open": count >= THRESHOLD and (now - last) < cooldown(count),
            "retry_in": max(0.0, round(cooldown(count) - (now - last), 1))
            if count >= THRESHOLD else 0.0,
        }
        for name, (count, last) in _failures.items()
    }
