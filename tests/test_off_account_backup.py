"""The disaster channel stays encrypted, independent and safe to repeat."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = (ROOT / "deploy" / "worker.ts").read_text(encoding="utf-8")
ACCOUNTS = (ROOT / "deploy" / "accounts.ts").read_text(encoding="utf-8")
TOOL = (ROOT / "deploy" / "backup-state.mjs").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable")
def test_encryption_and_strict_restore_replay_self_test():
    checked = subprocess.run(
        ["node", "deploy/backup-state.mjs", "self-test"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert checked.returncode == 0, checked.stderr
    assert '"self_test":true' in checked.stdout
    assert '"encrypted":true' in checked.stdout
    assert '"tamper_rejected":true' in checked.stdout
    assert '"replayed":true' in checked.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is unavailable")
def test_real_pull_commits_only_a_decryptable_replayable_artifact(tmp_path):
    token = "test-backup-token-" + "a" * 32
    bundle = {
        "format": "eesti-keelt-state",
        "version": 1,
        "made": "2026-01-01T00:00:00.000Z",
        "accounts": [],
        "learners": [{
            "who": {"scope": "owner", "id": "owner", "email": ""},
            "events": [{
                "id": "backfill", "type": "backfill",
                "ts": "2026-01-01T00:00:00.000+00:00", "v": 1,
                "learner": "owner", "payload": {"rows": 0},
            }],
        }],
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib handler contract
            if (self.path != "/api/backup/export" or
                    self.headers.get("authorization") != f"Bearer {token}"):
                self.send_response(403)
                self.end_headers()
                return
            body = json.dumps(bundle).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    public = tmp_path / "public.pem"
    private = tmp_path / "private.pem"
    out = tmp_path / "encrypted"
    env = {**os.environ, "BACKUP_TOKEN": token}
    try:
        commands = [
            ["node", "deploy/backup-state.mjs", "keygen",
             "--public", str(public), "--private", str(private)],
            ["node", "deploy/backup-state.mjs", "backup",
             "--url", f"http://127.0.0.1:{server.server_port}",
             "--public-key", str(public), "--private-key", str(private),
             "--out", str(out)],
        ]
        for command in commands:
            checked = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                     capture_output=True, timeout=30)
            assert checked.returncode == 0, checked.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    artifacts = list(out.glob("*.ekb"))
    assert len(artifacts) == 1
    assert artifacts[0].stat().st_mode & 0o777 == 0o600
    envelope = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert "learners" not in envelope and "accounts" not in envelope
    for command, marker in [
        (["verify"], '"verified":true'),
        (["restore"], '"dry_run":true'),
    ]:
        checked = subprocess.run(
            ["node", "deploy/backup-state.mjs", *command, str(artifacts[0]),
             "--private-key", str(private)],
            cwd=ROOT, text=True, capture_output=True, timeout=30,
        )
        assert checked.returncode == 0, checked.stderr
        assert marker in checked.stdout


def test_backup_channel_precedes_access_and_origin_dependencies():
    route = WORKER.index("await backupRoute(request, env)")
    origin = WORKER.index("if (!env.CLOUD_RUN_URL)", route)
    access = WORKER.index("requireAccess(env, ctx)", route)
    assert route < origin < access
    assert 'url.pathname === "/api/backup/export"' in WORKER
    assert 'url.pathname === "/api/backup/restore"' in WORKER


def test_read_and_restore_credentials_are_separate():
    assert "BACKUP_TOKEN?: string" in WORKER
    assert "RESTORE_TOKEN?: string" in WORKER
    assert "exporting ? env.BACKUP_TOKEN : env.RESTORE_TOKEN" in WORKER
    assert "env.BACKUP_TOKEN === env.RESTORE_TOKEN" in WORKER
    assert "BACKUP_TOKEN" in TOOL and "RESTORE_TOKEN" in TOOL


def test_restore_rejects_divergence_and_never_truncates_newer_history():
    assert "event restore diverges at position" in WORKER
    assert "appendEvidencePage" in WORKER
    assert "DELETE FROM events" not in WORKER[WORKER.index("async appendEvidencePage("):]
    assert "A newer live log may extend the backup. Never truncate it." in WORKER


def test_account_restore_checks_all_conflicts_before_inserting():
    restore = ACCOUNTS[ACCOUNTS.index("export function restoreAccounts("):]
    assert restore.index("for (const account of incoming)") < restore.index("let added = 0")
    assert "account restore conflicts" in restore
    assert "failures,locked_until" in restore


def test_backup_artifact_uses_authenticated_encryption_and_wrapped_keys():
    assert 'createCipheriv("aes-256-gcm"' in TOOL
    assert 'wrapping: "rsa-oaep-sha256"' in TOOL
    assert "cipher.setAAD" in TOOL and "decipher.setAAD" in TOOL
    assert "atomicWrite(target" in TOOL
