"""A notification that cannot be decrypted is a notification that never arrives.

Web Push fails quietly: the push service accepts the request, returns 201, and
the phone shows nothing. So the encryption (RFC 8291) and the VAPID signature
(RFC 8292) are checked against a real WebCrypto implementation rather than
trusted — `deploy/push.check.ts` decrypts what `deploy/push.ts` produced, with
the subscription's own private key.

The same script verifies that the key pair `cli push-keys` generates is a valid
P-256 pair: `eesti/vapid.py` does the curve arithmetic itself instead of adding
a compiled dependency for one command, and nothing else would catch a mistake
in it until the day a reminder was due.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "deploy" / "push.check.ts"


def run(*args: str) -> subprocess.CompletedProcess:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    return subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", str(CHECK), *args],
        cwd=ROOT, capture_output=True, text=True, timeout=120)


def test_a_notification_decrypts_with_the_subscriptions_own_key():
    done = run()
    assert done.returncode == 0, done.stderr or done.stdout
    assert "ok" in done.stdout


def test_the_key_pair_the_cli_makes_is_a_real_p256_pair():
    from eesti.vapid import generate

    public, private = generate()
    done = run(public, private)
    assert done.returncode == 0, done.stderr or done.stdout


def test_a_public_key_that_is_not_on_the_curve_is_refused():
    """The generator checks its own output; this pins that the check is real."""
    from eesti import vapid

    assert vapid.on_curve(*vapid.multiply(12345))
    x, y = vapid.multiply(12345)
    assert not vapid.on_curve(x, y + 1)
