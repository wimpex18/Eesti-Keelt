"""A missing private-service permission must stop deployment before secrets change."""
from pathlib import Path
import os
import subprocess
import shutil

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("status", [0, 1])
def test_configured_service_access_controls_the_deploy_gate(tmp_path, status):
    if not shutil.which("node") or not (ROOT / "node_modules/wrangler").exists():
        pytest.skip("VPC preflight requires Node and npm ci")
    config = tmp_path / "worker.jsonc"
    config.write_text('''{
      // The gate reads the real configuration shape, including comments.
      "vpc_services": [{"binding":"HOME_ASR","service_id":"test-service"}]
    }''')
    npx = tmp_path / "npx"
    npx.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$CALL_LOG"\nexit "$SERVICE_STATUS"\n')
    npx.chmod(0o755)
    log = tmp_path / "calls"
    result = subprocess.run(["bash", str(ROOT / "deploy/check-vpc-access.sh"), str(config)],
        cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "CALL_LOG": str(log), "SERVICE_STATUS": str(status)})
    assert log.exists(), result.stderr
    assert log.read_text().strip() == "wrangler vpc service get test-service"
    assert (result.returncode == 0) == (status == 0)
    if status:
        assert "Connectivity Directory Bind" in result.stdout
