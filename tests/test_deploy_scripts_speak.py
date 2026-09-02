"""A deploy script that fails must say so.

`bash deploy/set-llm-key.sh HF_TOKEN` printed **nothing at all** and exited 1.
Reported as "it didn't ask for the token".

The cause is one interaction, and the guard against it was already written:

    LINE="$(gcloud run services list --format='...' 2>/dev/null | head -1)"
    [ -n "$LINE" ] || { echo "ERROR: no Cloud Run service..." >&2; exit 1; }

Under `set -euo pipefail` a failing `gcloud` fails the pipeline, `pipefail`
propagates that to the assignment, and `set -e` kills the script **at that
line** — before the guard runs. Its stderr went to `/dev/null`, so the one
message that would have named the problem was discarded and the one that would
have replaced it was unreachable. The guard could only ever fire in the case it
was not written for: `gcloud` succeeding and returning nothing.

Three of the five scripts had it. `check-service.sh` reads through
`mapfile < <(...)`, whose failure does not trip `set -e`; `setup.sh` writes
`|| true`. That two of five were already right is why the fix is one sourced
function rather than a fourth copy.

Driven as real subprocesses against a stubbed `gcloud`, because every part of
this bug — `set -e`, `pipefail`, command substitution, a redirect — is shell
behaviour that no amount of reading the file reveals. `bash -n` parses all of
it happily, before and after.
"""

from __future__ import annotations

import os
import subprocess

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: The scripts that discover the service and then act on it. `check-service.sh`
#: is deliberately absent: it lists *every* service rather than taking the
#: first, which is a different job, and it was never broken.
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
        """Not merely "something went wrong". The provider named the cause —
        an API not enabled, a permission, an unset project — and which one it
        was decides what the operator does next."""
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
        """The shape that broke, asked of the directory. Three copies of six
        lines is how two of them stayed wrong after one was noticed."""
        for path in (ROOT / "deploy").glob("*.sh"):
            if path.name in ("_service.sh", "check-service.sh", "setup.sh"):
                continue
            body = path.read_text()
            if "gcloud run services list" in body:
                assert "find_service" in body, (
                    f"{path.name} lists services itself instead of sourcing "
                    f"_service.sh")

    def test_the_helper_never_discards_the_error_it_reports(self):
        """`2>/dev/null` on the discovery call is the whole bug. It may hide a
        *probe* — `gcloud config get-value` is allowed to be noisy — but not
        the call whose failure is the thing being explained.

        Comments stripped first. The helper quotes the broken original in its
        own header, and the first version of this assertion matched **that** —
        the fifth time this sprint a check has passed or failed on the prose
        explaining it rather than on the code.
        """
        code = "\n".join(
            line for line in
            (ROOT / "deploy" / "_service.sh").read_text().splitlines()
            if not line.lstrip().startswith("#"))
        listing = code[code.index("gcloud run services list"):]
        assert "2>/dev/null" not in listing[:400]
