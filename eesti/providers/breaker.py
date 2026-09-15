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

#: Set by `bind_later`; called once, when the breaker first needs storage, which
#: keeps the database path out of import time.
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
    """Bind to whatever `opener()` returns, the first time storage is needed, so the
    path is resolved only after callers have had a chance to redirect it.
    """
    global _store, _loaded, _opener
    _store = None
    _loaded = False
    _opener = opener


def _conn() -> sqlite3.Connection | None:
    """The store, opening it on first need. Never raises: an unbound breaker
    still works, it just forgets across restarts."""
    global _store, _opener
    if _store is None and _opener is not None:
        opener, _opener = _opener, None
        try:
            conn = opener()
            conn.executescript(SCHEMA)
            _store = conn
        except Exception:  # noqa: BLE001 - storage is an optimisation, not a need
            _store = None
    return _store


def _load() -> None:
    global _loaded
    store = _conn()
    if _loaded or store is None:
        return
    _loaded = True
    try:
        for row in store.execute("SELECT name, failures, last FROM breaker"):
            # Memory wins: it is this process's own, more recent evidence.
            _failures.setdefault(row[0], (row[1], row[2]))
    except sqlite3.Error:
        pass


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
    store = _conn()
    if store is not None:
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
    store = _conn()
    if store is not None:
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
    store = _conn()
    if store is not None:
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
