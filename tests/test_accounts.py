"""The Worker account and session helpers use real Node WebCrypto."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "deploy" / "accounts.check.ts"


def test_passwords_sessions_unlimited_accounts_and_removal():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    done = subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", str(CHECK)],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert done.returncode == 0, done.stderr or done.stdout
    assert done.stdout.strip() == "ok"
