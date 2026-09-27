"""Guest sandboxes on disk (ADR-0006): made on first use, dropped when idle.

Each sandbox is `config.GUEST_DIR/<name>/` with its own five learner files.
Nothing here is ever snapshotted or copied to the Durable Object, and a cold
start on Cloud Run removes all of it, which is intended.

SKELETON. `docs/identity.md` ("Guest sandboxes") is the specification.
"""

from __future__ import annotations

from pathlib import Path

#: More than this many sandboxes and the one idle longest is dropped.
MAX_SANDBOXES = 50
#: A sandbox untouched this long is dropped at the next sweep.
IDLE_HOURS = 24


def path(sandbox: str) -> Path:
    """The sandbox's directory. `sandbox` is already `identity.sandbox_name`-safe."""
    from . import config

    return Path(config.GUEST_DIR) / sandbox


def ensure(sandbox: str) -> Path:
    """Create the sandbox if new, and mark it used now.

    A new sandbox's log starts with the `backfill` marker, so `evidence.record`
    never treats it as an unrestored owner log (`NotRestored`).

    TODO(Luna): mkdir; write the marker once; touch a `last-used` file (its
    mtime is the idle clock); call `sweep()` at most once a minute.
    """
    raise NotImplementedError


def sweep() -> list[str]:
    """Drop sandboxes idle past `IDLE_HOURS`, then the oldest past `MAX_SANDBOXES`.

    Returns the names dropped. Never touches `shared.db` or anything outside
    `config.GUEST_DIR`. TODO(Luna).
    """
    raise NotImplementedError


def reset(sandbox: str) -> None:
    """Remove one sandbox entirely (`POST /api/guest/reset`). TODO(Luna)."""
    raise NotImplementedError
