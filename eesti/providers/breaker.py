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
drift into two behaviours, so it lives here and both import it. State is keyed
by provider name and is process-local, which is right for a single-user app and
would need rethinking if this ever served several.
"""

from __future__ import annotations

import time

THRESHOLD = 2
COOLDOWN = 900.0  # seconds

_failures: dict[str, tuple[int, float]] = {}


def is_open(name: str) -> bool:
    """True when this provider should be skipped for now."""
    count, last = _failures.get(name, (0, 0.0))
    return count >= THRESHOLD and (time.monotonic() - last) < COOLDOWN


def record_failure(name: str) -> None:
    count, _ = _failures.get(name, (0, 0.0))
    _failures[name] = (count + 1, time.monotonic())


def record_success(name: str) -> None:
    _failures.pop(name, None)


def reset() -> None:
    """Clear all breaker state — for tests, and for an explicit 'retry now'."""
    _failures.clear()


def state() -> dict[str, dict]:
    """What is currently tripped, for the UI and for `cli keys`."""
    now = time.monotonic()
    return {
        name: {
            "failures": count,
            "open": count >= THRESHOLD and (now - last) < COOLDOWN,
            "retry_in": max(0.0, round(COOLDOWN - (now - last), 1))
            if count >= THRESHOLD else 0.0,
        }
        for name, (count, last) in _failures.items()
    }
