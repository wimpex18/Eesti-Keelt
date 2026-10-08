"""`deploy/setup-backup.sh` against a stubbed `gcloud`.

A backup bucket that is public, keeps nothing, or lets the origin delete what
it wrote is not a backup; a script that recreates it would fail on the second
run.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "deploy" / "setup-backup.sh"

GCLOUD = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "$STUB_DIR/calls"
case "$*" in
  "config get-value project") echo test-project ;;
  "run services list"*) echo "eesti-keelt europe-north1" ;;
  *"serviceAccountName"*) printf '%s\n' "${STUB_SA:-}" ;;
  "projects describe"*) echo 123456789 ;;
  "projects get-iam-policy"*) printf '%s\n' ${STUB_PROJECT_ROLES:-} ;;
  "storage buckets describe"*) [ -f "$STUB_DIR/bucket" ] ;;
  "storage buckets create"*) touch "$STUB_DIR/bucket" ;;
  "storage buckets update"*"--lifecycle-file"*)
    file="$(printf '%s\n' "$@" | sed -n 's/^--lifecycle-file=//p')"
    cp "$file" "$STUB_DIR/lifecycle.json" ;;
esac
"""


@pytest.fixture
def run(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "gcloud").write_text(GCLOUD)
    (bin_dir / "gcloud").chmod(0o755)

    def go(**env: str) -> tuple[subprocess.CompletedProcess, list[str]]:
        (tmp_path / "calls").unlink(missing_ok=True)
        result = subprocess.run(
            ["bash", str(SCRIPT)], capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
                 "STUB_DIR": str(tmp_path), **env})
        calls = (tmp_path / "calls").read_text().splitlines()
        return result, calls

    go.dir = tmp_path
    return go


def test_a_private_bucket_the_service_can_only_add_to(run):
    result, calls = run(STUB_SA="grove-run@test-project.iam.gserviceaccount.com")
    assert result.returncode == 0, result.stderr
    create = next(c for c in calls if c.startswith("storage buckets create"))
    assert "gs://test-project-grove-backups" in create
    assert "--uniform-bucket-level-access" in create
    assert "--public-access-prevention" in create
    assert "--location europe-north1" in create
    grant = next(c for c in calls if "add-iam-policy-binding" in c)
    assert "--member=serviceAccount:grove-run@test-project.iam.gserviceaccount.com" in grant
    assert "--role=roles/storage.objectCreator" in grant
    lifecycle = json.loads((run.dir / "lifecycle.json").read_text())
    assert lifecycle["rule"][0]["action"]["type"] == "Delete"
    assert lifecycle["rule"][0]["condition"]["age"] == 180
    env = next(c for c in calls if c.startswith("run services update"))
    assert "EESTI_BACKUP_BUCKET=test-project-grove-backups" in env


def test_running_it_again_keeps_the_bucket(run):
    run()
    result, calls = run()
    assert result.returncode == 0, result.stderr
    assert not any(c.startswith("storage buckets create") for c in calls)


def test_the_default_account_and_wide_roles_are_named(run):
    result, calls = run(STUB_SA="", STUB_PROJECT_ROLES="roles/editor")
    assert result.returncode == 0, result.stderr
    grant = next(c for c in calls if "add-iam-policy-binding" in c)
    assert "123456789-compute@developer.gserviceaccount.com" in grant
    assert "roles/editor" in result.stdout
