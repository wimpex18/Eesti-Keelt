"""The image installs `requirements.lock`, not `requirements.txt`.

A package added to the request list but not re-locked is absent in production
(an import error on the first request that needs it), and a pin without a hash
fails `pip install --require-hashes` in the image build.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _name(raw: str) -> str:
    return re.sub(r"[-_.]+", "-", raw).lower()


def _requested() -> set[str]:
    names = set()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(_name(re.match(r"[A-Za-z0-9_.-]+", line).group(0)))
    return names


def _locked() -> dict[str, list[str]]:
    """Each pinned package and the hashes listed under it."""
    pins: dict[str, list[str]] = {}
    current = None
    for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines():
        pin = re.match(r"([A-Za-z0-9_.-]+)==\S+", line)
        if pin:
            current = _name(pin.group(1))
            pins[current] = []
        if current and "--hash=sha256:" in line:
            pins[current].append(line)
        if line.strip().startswith("#"):
            current = None
    return pins


def test_every_requested_package_is_locked():
    missing = _requested() - set(_locked())
    assert not missing, (f"{sorted(missing)} requested but not locked; re-run the command "
                         "in the header of requirements.lock")


def test_every_pin_carries_a_hash():
    unhashed = [name for name, hashes in _locked().items() if not hashes]
    assert not unhashed, unhashed
