"""The nightly copy of a permanent learner's event log, outside Cloudflare.

The Worker's cron has each account's Durable Object send its log, the replay
authority, here (`POST /api/state/backup`). The log is replayed strictly in
temporary stores, as `cli verify-backup` does, and only a log that replays is
written to a private Cloud Storage bucket (`EESTI_BACKUP_BUCKET`).

The service account is granted object-create on that bucket and nothing else
there (`deploy/setup-backup.sh`): without a broader project-wide role it can
neither read, overwrite nor delete a copy, so a compromised origin cannot
erase the history it would be restored from. Each copy gets a new name and the
upload refuses to replace an existing object.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

#: Cloud Run's own identity; no key is stored anywhere.
METADATA_TOKEN = ("http://metadata.google.internal/computeMetadata/v1/"
                  "instance/service-accounts/default/token")
UPLOAD = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"

#: A replay of the owner's log takes tens of seconds; past this, something is
#: wrong. Kept inside Cloud Run's default 300 s request timeout.
VERIFY_TIMEOUT = 240


class NotConfigured(RuntimeError):
    """No bucket named on this deployment."""


class UploadFailed(RuntimeError):
    """The bucket or the metadata server refused or did not answer."""


def bucket() -> str:
    name = os.environ.get("EESTI_BACKUP_BUCKET", "").strip()
    if not name:
        raise NotConfigured("EESTI_BACKUP_BUCKET is not set")
    return name


def _http(request: urllib.request.Request, timeout: float) -> bytes:
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed hosts
        return response.read()


def verify(log: bytes) -> dict:
    """Replay the log twice in temporary stores, in a separate process.

    `recovery.verify_export` points the owner's database paths at temporary
    files while it runs; inside the serving process that would briefly send
    other requests there too, so it runs as `cli verify-backup` instead.
    """
    from . import config

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as file:
        file.write(log)
        path = Path(file.name)
    try:
        done = subprocess.run(
            [sys.executable, "-m", "eesti.cli", "verify-backup", str(path)],
            capture_output=True, text=True, timeout=VERIFY_TIMEOUT, cwd=config.ROOT,
            env={**os.environ, "EESTI_DB": str(config.DB_PATH),
                 "EESTI_CONTENT_DB": str(config.CONTENT_DB)},
        )
    finally:
        path.unlink(missing_ok=True)
    if done.returncode != 0:
        reason = (done.stderr.strip().splitlines() or ["verification failed"])[-1]
        raise ValueError(reason[:300])
    return json.loads(done.stdout)


def _token() -> str:
    request = urllib.request.Request(METADATA_TOKEN, headers={"Metadata-Flavor": "Google"})
    return json.loads(_http(request, timeout=10))["access_token"]


def store(account: str, compressed: bytes, now: datetime | None = None) -> dict:
    """Verify a gzipped JSONL log and write it as a new object. Raises
    `ValueError` for a log that does not replay, `NotConfigured` without a bucket."""
    target = bucket()
    try:
        log = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise ValueError("not a gzip stream") from exc
    report = verify(log)
    now = now or datetime.now(timezone.utc)
    digest = hashlib.sha256(log).hexdigest()
    name = f"events/{account}/{now:%Y/%m/%d}/{now:%Y%m%dT%H%M%S%fZ}-{digest[:16]}.jsonl.gz"
    query = urllib.parse.urlencode({"uploadType": "media", "name": name,
                                    "ifGenerationMatch": "0"})
    try:
        request = urllib.request.Request(
            UPLOAD.format(bucket=urllib.parse.quote(target, safe="")) + "?" + query,
            data=compressed, method="POST",
            headers={"Authorization": f"Bearer {_token()}",
                     "Content-Type": "application/gzip"})
        _http(request, timeout=120)
    except urllib.error.HTTPError as exc:
        # 403 is usually a missing bucket grant for the runtime service account.
        raise UploadFailed(f"storage answered HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise UploadFailed(f"storage unreachable: {type(exc).__name__}") from None
    return {"verified": True, "events": report.get("events", 0), "object": name,
            "bytes": len(compressed), "sha256": digest}
