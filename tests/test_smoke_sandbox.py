"""Live QA must refuse a submission until Worker and origin agree on guest scope."""
from pathlib import Path
import os
import subprocess

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("worker,origin", [
    ('{"scope":"owner"}', '{"scope":"guest"}'),
    ('{"scope":"guest"}', '{"scope":"owner"}'),
    ('404', '{"scope":"guest"}'),
    ('{"scope":"guest"}', '404'),
    ('not-json', '{"scope":"guest"}'),
])
def test_unconfirmed_isolation_never_submits(tmp_path, worker, origin):
    result, calls = run_probe(tmp_path, worker, origin)
    assert result.returncode != 0
    assert "POST" not in calls


def test_confirmed_guest_keeps_the_same_sandbox_on_submission(tmp_path):
    result, calls = run_probe(tmp_path, '{"scope":"guest"}', '{"scope":"guest"}')
    assert result.returncode == 0, result.stderr
    assert calls.count("x-eesti-guest: smoke-42-2") == 3
    assert "POST" in calls


def run_probe(tmp_path, worker, origin):
    log = tmp_path / "calls"
    script = r'''
set -euo pipefail
auth=(-H "CF-Access-Client-Id: test")
curl() {
  printf '%s\n' "$*" >> "$CALL_LOG"
  case "${*: -1}" in
    */api/auth/me) [ "$WORKER_REPLY" != 404 ] || return 22; printf '%s' "$WORKER_REPLY" ;;
    */api/me) [ "$ORIGIN_REPLY" != 404 ] || return 22; printf '%s' "$ORIGIN_REPLY" ;;
    */api/check) printf '%s' '{}' ;;
    *) return 1 ;;
  esac
}
if source "$SANDBOX_SCRIPT"; then
  curl "${auth[@]}" -X POST "$URL/api/check"
else
  exit 1
fi
'''
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
        env={**os.environ, "URL": "https://learn.test", "GITHUB_RUN_ID": "42",
             "GITHUB_RUN_ATTEMPT": "2", "CALL_LOG": str(log),
             "WORKER_REPLY": worker, "ORIGIN_REPLY": origin,
             "SANDBOX_SCRIPT": str(ROOT / "deploy/smoke-sandbox.sh")})
    return result, log.read_text()
