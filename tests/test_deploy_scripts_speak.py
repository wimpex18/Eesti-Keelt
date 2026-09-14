"""A deploy script that fails must say why.

Under `set -euo pipefail`, `LINE="$(gcloud ... 2>/dev/null | head -1)"` exits
at that line when `gcloud` fails — before any guard, with the error discarded.
The scripts share one sourced helper (`deploy/_service.sh`) that reports what
`gcloud` said.

Driven as real subprocesses against a stubbed `gcloud`: `set -e`, `pipefail`,
command substitution and redirects are shell behaviour that reading the file
(or `bash -n`) cannot reveal.
"""

from __future__ import annotations

import os
import subprocess

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: Scripts that discover one service and act on it. `check-service.sh` lists every
#: service instead, a different job.
ACTING = {
    "set-llm-key.sh": ["HF_TOKEN"],
    "push-content.sh": [],
    "reset-progress.sh": ["--everything"],
}

FAILING_GCLOUD = """#!/usr/bin/env bash
case "$1 $2" in
  "config get-value") echo "eesti-keelt-prod";;
  "run services")
      echo "ERROR: (gcloud.run.services.list) PERMISSION_DENIED: denied" >&2
      exit 1;;
  *) exit 1;;
esac
"""

NO_PROJECT_GCLOUD = """#!/usr/bin/env bash
case "$1 $2" in
  "config get-value") echo "(unset)";;
  "projects list") echo "some-project Some Project";;
  *) exit 1;;
esac
"""


def _run(script: str, argv: list[str], gcloud: str, tmp_path: Path):
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    (stub / "gcloud").write_text(gcloud)
    (stub / "gcloud").chmod(0o755)
    env = {**os.environ, "PATH": f"{stub}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(
        ["bash", f"deploy/{script}", *argv],
        cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True)


@pytest.mark.parametrize("script", sorted(ACTING))
class TestAFailureIsNeverSilent:
    def test_it_says_something_when_gcloud_fails(self, script, tmp_path):
        done = _run(script, ACTING[script], FAILING_GCLOUD, tmp_path)
        assert done.returncode != 0
        assert (done.stdout + done.stderr).strip(), (
            f"deploy/{script} failed and printed nothing — the silent exit is "
            f"back")

    def test_it_repeats_what_gcloud_actually_said(self, script, tmp_path):
        """The error repeats what `gcloud` actually said (API not enabled, permission,
        unset project).
        """
        done = _run(script, ACTING[script], FAILING_GCLOUD, tmp_path)
        assert "PERMISSION_DENIED" in done.stdout + done.stderr

    def test_an_unset_project_is_told_apart_from_a_missing_service(
            self, script, tmp_path):
        """The commoner of the two in a fresh Cloud Shell, and the only one
        with a one-line fix. Reporting it as "no Cloud Run service" sends the
        operator to the wrong console page."""
        done = _run(script, ACTING[script], NO_PROJECT_GCLOUD, tmp_path)
        out = done.stdout + done.stderr
        assert done.returncode != 0
        assert "gcloud config set project" in out


class TestTheGuardIsWrittenOnce:
    def test_no_script_rediscovers_the_service_for_itself(self):
        """No script rediscovers the service itself; all use the helper."""
        for path in (ROOT / "deploy").glob("*.sh"):
            if path.name in ("_service.sh", "check-service.sh", "setup.sh"):
                continue
            body = path.read_text()
            if "gcloud run services list" in body:
                assert "find_service" in body, (
                    f"{path.name} lists services itself instead of sourcing "
                    f"_service.sh")

    def test_the_helper_never_discards_the_error_it_reports(self):
        """The helper never sends the discovery call's stderr to `/dev/null` (comments
        stripped before checking).
        """
        code = "\n".join(
            line for line in
            (ROOT / "deploy" / "_service.sh").read_text().splitlines()
            if not line.lstrip().startswith("#"))
        listing = code[code.index("gcloud run services list"):]
        assert "2>/dev/null" not in listing[:400]
