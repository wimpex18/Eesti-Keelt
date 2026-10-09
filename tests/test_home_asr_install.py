"""`deploy/home-asr/install.sh` as an updater, against stubbed tools.

Updating the Mac mini must be one command that actually moves its packages:
a re-run that keeps yesterday's torch, or that demands the tunnel token again,
leaves the home service on versions the ASR bench never measured.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "deploy" / "home-asr" / "install.sh"

UV = r"""#!/bin/sh
echo "uv $*" >> "$STUB_LOG"
if [ "$1" = pip ] && [ "$STUB_INSTALL_FAIL" = 1 ]; then exit 17; fi
if [ "$1" = venv ]; then
  for last; do :; done
  mkdir -p "$last/bin"
  cat > "$last/bin/python" <<'PY'
#!/bin/sh
case "$*" in
  *snapshot_download*) echo /models/stub ;;
  *secrets*) echo service-secret ;;
esac
PY
  chmod +x "$last/bin/python"
fi
"""

CURL = r"""#!/bin/sh
echo "curl $*" >> "$STUB_LOG"
case "$*" in
  *cloudflared*) cat "$STUB_TGZ" ;;
  *health*) echo '{"ok":true}' ;;
esac
"""


@pytest.fixture(params=["x86_64", "arm64"])
def install(tmp_path, request):
    if not shutil.which("zsh"):
        pytest.skip("zsh is not installed")
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    bin_dir.mkdir()
    home.mkdir()
    for name, body in (("uv", UV), ("curl", CURL)):
        (bin_dir / name).write_text(body)
        (bin_dir / name).chmod(0o755)
    (bin_dir / "uname").write_text(f"#!/bin/sh\necho {request.param}\n")
    (bin_dir / "uname").chmod(0o755)
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "cloudflared").write_text("#!/bin/sh\n")
    subprocess.run(["tar", "-czf", str(tmp_path / "cf.tgz"), "-C", str(payload), "cloudflared"],
                   check=True)
    log = tmp_path / "log"

    def run(*args: str, fail_install=False) -> tuple[subprocess.CompletedProcess, list[str]]:
        log.write_text("")
        result = subprocess.run(
            ["zsh", str(SCRIPT), *args], capture_output=True, text=True, timeout=60,
            env={**os.environ, "HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}",
                 "STUB_LOG": str(log), "STUB_TGZ": str(tmp_path / "cf.tgz"),
                 "STUB_INSTALL_FAIL": "1" if fail_install else "0",
                 "EESTI_HOME_ASR_DRY_RUN": "1"})
        return result, log.read_text().splitlines()

    run.state = home / ".eesti-home-asr"
    run.arch = request.param
    return run


def test_an_update_needs_no_token_and_moves_every_package(install):
    first, _ = install("tunnel-token-from-cloudflare")
    assert first.returncode == 0, first.stderr
    again, calls = install()
    assert again.returncode == 0, again.stderr
    assert (install.state / "tunnel-token").read_text().strip() == "tunnel-token-from-cloudflare"
    installs = [c for c in calls if c.startswith("uv pip install")]
    assert installs and all("--upgrade" in c for c in installs)
    if install.arch == "x86_64":
        assert any("av==18.1.0" in c for c in installs)
    else:
        assert any("-r requirements-local-asr.txt" in c for c in installs)
        assert all("av==18.1.0" not in c for c in installs)
    assert any("cloudflared" in c for c in calls if c.startswith("curl")), \
        "the tunnel client is refreshed too"


def test_a_first_install_still_asks_for_the_token(install):
    result, _ = install()
    assert result.returncode != 0
    assert "Usage" in result.stderr


def test_failed_package_install_stops_before_rewriting_service_scripts(install):
    first, _ = install("tunnel-token-from-cloudflare")
    assert first.returncode == 0, first.stderr
    runner = install.state / "run-asr.sh"
    before = runner.read_bytes()
    result, _ = install(fail_install=True)
    assert result.returncode == 17
    assert runner.read_bytes() == before
    assert "Downloading" not in result.stdout
    assert "Waiting for the model" not in result.stdout
