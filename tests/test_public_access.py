"""Public entry cannot expose owner material or elevate a new visitor."""
from __future__ import annotations

import importlib.util
import io
import json
import sqlite3
from pathlib import Path

import pytest

from eesti import config, identity, sources


@pytest.mark.parametrize("scope", [identity.GUEST, identity.LEARNER])
def test_public_content_reads_and_direct_ids_exclude_personal_imports(client, scope, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONTENT_DB", tmp_path / "public.db")
    public = sources.Item(source_id="generated", skill="lugemine", title="Avalik tekst",
                          body="Ma loen täna kodus head raamatut.")
    private = sources.Item(source_id="oma-materjal", skill="lugemine", title="Oma tekst",
                           body="Ta kirjutab täna sõbrale pika kirja.")
    conn = sources.connect(config.CONTENT_DB)
    sources.register(conn)
    sources.add_items(conn, [public, private])
    with conn:
        conn.execute("INSERT INTO topic_items VALUES (?,?,?)", ("obj-case", private.id, 1))
        conn.execute("INSERT INTO topic_items VALUES (?,?,?)", ("obj-case", public.id, 1))
    conn.close()
    headers = {"x-eesti-scope": scope, "x-eesti-guest": "public-test"}
    if scope == identity.LEARNER:
        headers["x-eesti-learner"] = "l-0123456789abcdef"
    listed = client.get("/api/library", headers=headers).json()
    assert {row["id"] for row in listed["items"]} == {public.id}
    assert client.get(f"/api/library/{public.id}", headers=headers).status_code == 200
    for path in (f"/api/library/{private.id}", f"/api/exam/file/{private.id}",
                 f"/api/exam/text/{private.id}", f"/api/exam/native/{private.id}"):
        assert client.get(path, headers=headers).status_code == 404, path
    with identity.use(identity.Scope(scope, id="public-test")):
        scoped = sources.connect(config.CONTENT_DB)
        assert [r[0] for r in scoped.execute("SELECT item_id FROM topic_items")] == [public.id]
        with pytest.raises(sqlite3.OperationalError):
            scoped.execute("DELETE FROM items")
        scoped.close()
    assert client.get(f"/api/library/{private.id}", headers={"x-eesti-scope": "owner"}).status_code == 200


def test_personal_sentence_recordings_never_serve_public_requests(client, monkeypatch, tmp_path):
    from eesti import haaldus
    from eesti.api.speech import _human, _human_passages
    path = tmp_path / "audio.db"
    monkeypatch.setattr(config, "AUDIO_DB", path)
    conn = haaldus.connect(path)
    text = "Ma loen täna kodus head raamatut."
    with conn:
        conn.execute("INSERT INTO sentence_audio VALUES (?,?,?,?,?)", (text, 7, "audio/wav", b"private", "owner"))
    conn.close()
    assert _human(text).body == b"private"
    assert _human(text).headers["cache-control"] == "private, no-store"
    for kind in (identity.GUEST, identity.LEARNER):
        with identity.use(identity.Scope(kind, id="public-audio")):
            assert _human(text) is None
            assert _human_passages(1, 1) == []


def migration():
    spec = importlib.util.spec_from_file_location("public_migration", Path(__file__).parents[1] / "deploy/open-public-access.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENV = {"WORKER_URL": "https://grove.example.workers.dev", "CLOUD_RUN_URL": "https://origin.test",
       "PROXY_TOKEN": "test-proxy", "CLOUDFLARE_API_TOKEN": "test-cf", "CLOUDFLARE_ACCOUNT_ID": "test-account"}


class Shell:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return b"<title>Grove</title>"


def test_public_checks_identify_the_deployer_without_forwarding_credentials(monkeypatch):
    """An already public Worker must not fail deployment on a Python-UA block."""
    module = migration()
    public_requests = []

    def urlopen(request, **kwargs):
        url = request.full_url
        headers = {name.lower(): value for name, value in request.header_items()}
        if headers.get("user-agent") != "Grove-deploy/1.0":
            raise module.HTTPError(url, 403, "Forbidden", {}, None)
        if url.startswith(ENV["CLOUD_RUN_URL"]):
            assert headers["x-proxy-token"] == ENV["PROXY_TOKEN"]
            assert headers["x-eesti-scope"] == "guest"
            return io.BytesIO(json.dumps({"public_access": True, "origin_guarded": True}).encode())
        if url.startswith(module.API):
            assert headers["authorization"] == "Bearer " + ENV["CLOUDFLARE_API_TOKEN"]
            return io.BytesIO(b'{"success": true, "result": []}')
        public_requests.append(url)
        assert set(headers) == {"user-agent"}
        if url.endswith("/api/auth/me"):
            return io.BytesIO(b'{"scope": "guest"}')
        if url.endswith("/api/health"):
            return io.BytesIO(b'{"public_access": true}')
        return Shell()

    monkeypatch.setattr(module, "urlopen", urlopen)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    module.open_public(ENV)
    assert public_requests == [ENV["WORKER_URL"] + path
                               for path in ("/api/auth/me", "/api/health", "/")]


def test_migration_waits_for_safe_origin_and_deletes_only_exact_hostname(monkeypatch):
    module = migration()
    calls = []
    checks = 0
    def request(url, **kwargs):
        nonlocal checks
        calls.append((url, kwargs.get("method", "GET")))
        if "origin.test" in url:
            checks += 1
            return {"public_access": checks >= 2, "origin_guarded": True}
        if "access/apps?" in url:
            return {"success": True, "result": [
                {"id": "target", "domain": "grove.example.workers.dev"},
                {"id": "other", "domain": "other.example.workers.dev"},
                {"id": "wildcard", "domain": "*.example.workers.dev"}]}
        if url.endswith("/target"):
            return {"success": True}
        if url.endswith("/api/auth/me"):
            return {"scope": "guest"}
        return {"public_access": True}
    monkeypatch.setattr(module, "request_json", request)
    monkeypatch.setattr(module.time, "sleep", lambda n: None)
    monkeypatch.setattr(module, "urlopen", lambda *a, **kw: Shell())
    module.open_public(ENV)
    assert checks == 2
    assert [url.rsplit("/", 1)[1] for url, method in calls if method == "DELETE"] == ["target"]


def test_migration_cannot_open_an_old_origin_or_shared_application(monkeypatch):
    module = migration()
    monkeypatch.setattr(module.time, "sleep", lambda n: None)
    monkeypatch.setattr(module, "request_json", lambda url, **kw: {"origin_guarded": True})
    with pytest.raises(RuntimeError, match="has not deployed"):
        module.open_public(ENV)
    def shared(url, **kwargs):
        assert kwargs.get("method") != "DELETE"
        if "origin.test" in url:
            return {"public_access": True, "origin_guarded": True}
        return {"success": True, "result": [{"id": "shared", "domain": "grove.example.workers.dev",
                "self_hosted_domains": ["grove.example.workers.dev", "other.test"]}]}
    monkeypatch.setattr(module, "request_json", shared)
    with pytest.raises(RuntimeError, match="other domains"):
        module.open_public(ENV)


def test_migration_failure_is_visible_and_repeat_deploy_is_idempotent(monkeypatch):
    module = migration()
    monkeypatch.setattr(module, "urlopen", lambda *a, **kw: Shell())
    def request(url, **kwargs):
        if "origin.test" in url:
            return {"public_access": True, "origin_guarded": True}
        if "access/apps?" in url:
            return {"success": False}
        return {"scope": "guest", "public_access": True}
    monkeypatch.setattr(module, "request_json", request)
    with pytest.raises(RuntimeError, match="permissions"):
        module.open_public(ENV)
    def already_public(url, **kwargs):
        assert kwargs.get("method") != "DELETE"
        if "access/apps?" in url:
            return {"success": True, "result": []}
        return {"public_access": True, "origin_guarded": True, "scope": "guest"}
    monkeypatch.setattr(module, "request_json", already_public)
    module.open_public(ENV)


def test_migration_matches_destinations_and_names_a_remaining_gate(monkeypatch):
    module = migration()
    assert module.matching_apps([
        {"id": "new", "destinations": [{"type": "public", "uri": "grove.example.workers.dev/*"}]},
        {"id": "wild", "destinations": [{"type": "public", "uri": "*.example.workers.dev"}]},
    ], "grove.example.workers.dev") == [
        {"id": "new", "destinations": [{"type": "public", "uri": "grove.example.workers.dev/*"}]}]
    def gated(url, **kwargs):
        if "origin.test" in url:
            return {"public_access": True, "origin_guarded": True}
        if "access/apps?" in url:
            return {"success": True, "result": [{"id": "wild", "domain": "*.example.workers.dev"}]}
        raise module.HTTPError(url, 403, "Forbidden", {}, None)
    monkeypatch.setattr(module, "request_json", gated)
    with pytest.raises(RuntimeError, match="still behind a login gate"):
        module.open_public(ENV)
