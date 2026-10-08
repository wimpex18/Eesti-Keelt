"""Guest sandboxes on disk (ADR-0006): made on first use, dropped when idle.

Each sandbox is `config.GUEST_DIR/<name>/` with its own five learner files.
Nothing here is ever snapshotted or copied to the Durable Object, and a cold
start on Cloud Run removes all of it, which is intended.

`docs/identity.md` ("Guest sandboxes") is the specification.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

#: More than this many sandboxes and those idle at least `RESTING_MINUTES`
#: are dropped, longest idle first.
MAX_SANDBOXES = 50
#: A sandbox used more recently is mid-session and is kept over the soft limit.
RESTING_MINUTES = 60
#: Cloud Run's disk is memory: past this many, the longest idle goes regardless.
HARD_MAX_SANDBOXES = 200
#: A sandbox untouched this long is dropped at the next sweep.
IDLE_HOURS = 24
_last_sweep = 0.0


def path(sandbox: str) -> Path:
    """The sandbox's directory. `sandbox` is already `identity.sandbox_name`-safe."""
    from . import config

    return Path(config.GUEST_DIR) / sandbox


def ensure(sandbox: str) -> Path:
    """Create the sandbox if new, and mark it used now.

    A new sandbox's log starts with the `backfill` marker, so `evidence.record`
    never treats it as an unrestored owner log (`NotRestored`).

    The caller has already resolved `sandbox` with `identity.sandbox_name`.
    """
    global _last_sweep

    directory = path(sandbox)
    directory.mkdir(parents=True, exist_ok=True)
    from . import evidence

    with evidence.connect() as log:
        if not evidence.has_backfill(log):
            evidence.backfill(log)
    used = directory / "last-used"
    used.touch()
    now = time.monotonic()
    if now - _last_sweep >= 60:
        sweep()
        _last_sweep = now
    return directory


def sweep() -> list[str]:
    """Drop sandboxes idle past `IDLE_HOURS`; past `MAX_SANDBOXES`, the longest
    idle of those resting `RESTING_MINUTES`; past `HARD_MAX_SANDBOXES`, the
    longest idle of any.

    Returns the names dropped. Removes nothing outside `config.GUEST_DIR`.
    """
    from . import config

    root = Path(config.GUEST_DIR)
    if not root.exists():
        return []
    now = time.time()
    entries = [p for p in root.iterdir() if p.is_dir() and not p.is_symlink()]

    def used_at(directory: Path) -> float:
        marker = directory / "last-used"
        try:
            return marker.stat().st_mtime
        except OSError:
            try:
                return directory.stat().st_mtime
            except OSError:
                return 0.0

    removed: list[str] = []
    active = []
    for directory in entries:
        last = used_at(directory)
        if now - last > IDLE_HOURS * 60 * 60:
            shutil.rmtree(directory)
            removed.append(directory.name)
        else:
            active.append((last, directory))

    active.sort(key=lambda item: (item[0], item[1].name))
    resting = [item for item in active if now - item[0] >= RESTING_MINUTES * 60]
    surplus = len(active) - MAX_SANDBOXES
    dropped = resting[:max(0, surplus)]
    kept = [item for item in active if item not in dropped]
    dropped += kept[:max(0, len(kept) - HARD_MAX_SANDBOXES)]
    for _, directory in dropped:
        shutil.rmtree(directory)
        removed.append(directory.name)
    return removed


def reset(sandbox: str) -> None:
    """Remove one sandbox entirely (`POST /api/guest/reset`)."""
    directory = path(sandbox)
    if directory.exists() and directory.is_dir() and not directory.is_symlink():
        shutil.rmtree(directory)
