"""One circuit breaker, shared by every provider chain.

The grammar chain has had one since the research APIs turned out to hang for 61
seconds before failing: an endpoint that is down tends to stay down for hours,
and paying that timeout on every request makes the whole tool feel broken.

The speech chain needed the same thing and did not have it, which was worse
there than in grammar: speech has **four** engines and a long timeout each,
because a minute of audio takes real time to transcribe. A Cloudflare outage
therefore cost the learner every engine's timeout in series before they were
told anything — a multi-minute wait to be told nothing was heard.

Copying twenty lines of stateful logic into a second module is how two copies
drift into two behaviours, so it lives here and both import it.

**State outlives the process, and it has to.** It used to be a module-level
dict, described as process-local and "right for a single-user app". That was
wrong in exactly the environment this runs in. Cloud Run scales to zero, so a
learner who checks one paragraph in the evening gets a cold container almost
every time — and a cold container has an empty breaker. With a threshold of
two, the first *two* requests of every container lifetime paid the full
timeout. TartuNLP's grammar endpoint has returned 500 after ~61 seconds since
the research phase and was re-probed today with the same result, so at a 5
second provider timeout that was ten seconds of dead waiting per cold start,
for a service that has never once answered.

Wall-clock time, not `monotonic`: a monotonic timestamp means nothing to the
next process, and this state is now read by one.

The cooldown doubles with each failure beyond the threshold, up to about a
week. That is the re-probe cadence the plan asks for — often enough to notice a
recovery, rare enough that a permanently dead endpoint costs one timeout a week
instead of two per session. `reset()` forces an immediate retry.
"""

from __future__ import annotations

import sqlite3
import time

THRESHOLD = 2
COOLDOWN = 900.0  # seconds

#: Cap on the doubling. The plan's instruction is to re-probe the research APIs
#: weekly and compare against the regression set before promoting one, so there
#: is no value in backing off further than that.
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
_loaded = False


def bind(conn: sqlite3.Connection | None) -> None:
    """Give the breaker somewhere to remember, or `None` to forget.

    Optional on purpose: the CLI and the tests run without one, and a breaker
    that refused to work unbound would make every caller responsible for
    storage it does not care about.
    """
    global _store, _loaded
    _store = conn
    _loaded = False
    if conn is not None:
        conn.executescript(SCHEMA)


def _load() -> None:
    global _loaded
    if _loaded or _store is None:
        return
    _loaded = True
    try:
        for row in _store.execute("SELECT name, failures, last FROM breaker"):
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
    if _store is not None:
        try:
            _store.execute(
                "INSERT INTO breaker (name, failures, last) VALUES (?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET failures = ?, last = ?",
                (name, count + 1, now, count + 1, now),
            )
            _store.commit()
        except sqlite3.Error:
            pass  # a breaker that cannot write is still a working breaker


def record_success(name: str) -> None:
    _load()
    _failures.pop(name, None)
    if _store is not None:
        try:
            _store.execute("DELETE FROM breaker WHERE name = ?", (name,))
            _store.commit()
        except sqlite3.Error:
            pass


def reset() -> None:
    """Clear all breaker state — for tests, and for an explicit 'retry now'."""
    global _loaded
    _failures.clear()
    _loaded = True          # nothing to load; the caller means "try again now"
    if _store is not None:
        try:
            _store.execute("DELETE FROM breaker")
            _store.commit()
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
