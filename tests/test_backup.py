"""The nightly copy of each permanent learner's event log, outside Cloudflare.

A copy that does not replay is not a backup, and a copy that overwrites the
previous night's is one bad night from none. These run the origin half
(`POST /api/state/backup`) against a fake Cloud Storage.
"""

from __future__ import annotations

import gzip
import json
import urllib.parse

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import backup, config, evidence, vocab  # noqa: E402

TOKEN = "test-state-token"


@pytest.fixture
def storage(monkeypatch):
    """Record what would have reached the metadata server and the bucket."""
    calls = []

    def http(request, timeout):
        calls.append(request)
        url = request.full_url
        if url.startswith(backup.METADATA_TOKEN):
            return json.dumps({"access_token": "metadata-token", "expires_in": 3599}).encode()
        name = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["name"][0]
        return json.dumps({"name": name, "generation": "1"}).encode()

    monkeypatch.setattr(backup, "_http", http)
    monkeypatch.setenv("STATE_TOKEN", TOKEN)
    monkeypatch.setenv("EESTI_BACKUP_BUCKET", "grove-backups-test")
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return calls


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)


def _log() -> bytes:
    """The owner's log as the Durable Object holds it: one event per line."""
    with vocab.connect(config.VOCAB_DB) as words:
        vocab.set_status(words, "raamat", 99)
    with evidence.connect() as log:
        lines = [json.dumps(e.to_dict(), ensure_ascii=False) for e in evidence.events(log)]
    return ("\n".join(lines) + "\n").encode()


def _send(client, body: bytes, **headers):
    return client.post("/api/state/backup", content=gzip.compress(body), headers={
        "x-state-token": TOKEN, "content-type": "application/gzip", **headers})


def test_a_replayable_log_is_stored_under_a_new_name_each_night(client, storage):
    body = _log()
    first = _send(client, body)
    assert first.status_code == 200, first.text
    report = first.json()
    assert report["verified"] is True and report["events"] == body.count(b"\n")
    upload = storage[-1]
    query = urllib.parse.parse_qs(urllib.parse.urlparse(upload.full_url).query)
    # Never replaces an existing object: the account cannot overwrite history.
    assert query["ifGenerationMatch"] == ["0"]
    assert query["name"][0].startswith("events/owner/")
    assert upload.headers["Authorization"] == "Bearer metadata-token"
    assert gzip.decompress(upload.data) == body
    second = _send(client, body)
    assert second.json()["object"] != report["object"]


def test_a_log_that_does_not_replay_is_refused_and_nothing_is_stored(client, storage):
    body = _log() + json.dumps({"id": "x", "type": "future-unsupported", "ts":
                                "2026-10-08T00:00:00+00:00", "payload": {}}).encode() + b"\n"
    response = _send(client, body)
    assert response.status_code == 422
    assert "cannot replay" in response.json()["detail"]
    assert not [r for r in storage if "upload" in r.full_url]


def test_an_incomplete_log_is_refused(client, storage):
    response = _send(client, b"")
    assert response.status_code == 422
    assert "completeness" in response.json()["detail"]


def test_learner_logs_are_kept_apart(client, storage, monkeypatch):
    monkeypatch.setenv("PROXY_TOKEN", "test-proxy")
    body = _log()
    response = _send(client, body, **{"x-proxy-token": "test-proxy", "x-eesti-scope": "learner",
                                      "x-eesti-learner": "l-0123456789abcdef"})
    assert response.status_code == 200, response.text
    assert response.json()["object"].startswith("events/l-0123456789abcdef/")


def test_without_a_bucket_it_says_so(client, storage, monkeypatch):
    monkeypatch.delenv("EESTI_BACKUP_BUCKET")
    assert _send(client, _log()).status_code == 503


def test_the_platform_only(client, storage):
    response = client.post("/api/state/backup", content=gzip.compress(_log()))
    assert response.status_code == 403
