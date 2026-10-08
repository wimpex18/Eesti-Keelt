"""`deploy/set-item-secret.sh` against a stubbed `gcloud`.

Rotating the item secret wrongly would refuse every answer a learner queued
offline; printing it would put a signing key in a terminal scrollback.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "deploy" / "set-item-secret.sh"

GCLOUD = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "$STUB_DIR/calls"
case "$*" in
  "config get-value project") echo test-project ;;
  "run services list"*) echo "eesti-keelt europe-north1" ;;
  *"--format=json"*) cat "$STUB_DIR/service.json" ;;
  *"env.name"*) python3 -c 'import json,sys; print(";".join(e["name"] for e in json.load(open(sys.argv[1]))["spec"]["template"]["spec"]["containers"][0]["env"]))' "$STUB_DIR/service.json" ;;
  "run services update"*)
    last="${@: -1}"
    pairs="${last#^@^}"
    python3 - "$STUB_DIR/service.json" "$pairs" <<'PY'
import json, sys
path, pairs = sys.argv[1], sys.argv[2].split()[0]
doc = json.load(open(path))
env = doc["spec"]["template"]["spec"]["containers"][0]["env"]
for pair in pairs.split("@"):
    name, value = pair.split("=", 1)
    env[:] = [e for e in env if e["name"] != name] + [{"name": name, "value": value}]
json.dump(doc, open(path, "w"))
PY
    ;;
esac
"""


def _env_of(stub: Path) -> dict:
    doc = json.loads((stub / "service.json").read_text())
    return {e["name"]: e["value"]
            for e in doc["spec"]["template"]["spec"]["containers"][0]["env"]}


@pytest.fixture
def service(tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("openssl is not installed")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "gcloud").write_text(GCLOUD)
    (bin_dir / "gcloud").chmod(0o755)

    def run(env: dict, *args: str) -> tuple[subprocess.CompletedProcess, dict]:
        (tmp_path / "service.json").write_text(json.dumps({"spec": {"template": {"spec": {
            "containers": [{"env": [{"name": k, "value": v} for k, v in env.items()]}]}}},
            "status": {"url": "https://origin.test"}}))
        result = subprocess.run(
            ["bash", str(SCRIPT), *args], capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
                 "STUB_DIR": str(tmp_path)})
        return result, _env_of(tmp_path)

    return run


def test_a_first_run_sets_a_random_secret_without_printing_it(service):
    result, env = service({"PROXY_TOKEN": "guard"})
    assert result.returncode == 0, result.stderr
    assert re.fullmatch(r"[0-9a-f]{64}", env["ITEM_SECRET"])
    assert "ITEM_SECRET_PREVIOUS" not in env
    assert env["ITEM_SECRET"] not in result.stdout + result.stderr


def test_an_existing_secret_is_never_replaced_without_asking(service):
    result, env = service({"ITEM_SECRET": "a" * 64})
    assert result.returncode == 0, result.stderr
    assert env == {"ITEM_SECRET": "a" * 64}


def test_rotation_keeps_the_old_secret_verifying(service):
    old = "b" * 64
    result, env = service({"ITEM_SECRET": old, "ITEM_SECRET_PREVIOUS": "c" * 64}, "--rotate")
    assert result.returncode == 0, result.stderr
    assert env["ITEM_SECRET_PREVIOUS"] == old
    assert env["ITEM_SECRET"] not in (old, "c" * 64)
    output = result.stdout + result.stderr
    assert old not in output and env["ITEM_SECRET"] not in output
