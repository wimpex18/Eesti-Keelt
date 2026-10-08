"""Guests can use every exercise without writing into permanent learner state."""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

import pytest

from eesti import config, guest, identity

GUEST = {"x-eesti-scope": "guest", "x-eesti-guest": "t1"}
STATE = {"x-state-token": "state-secret", **GUEST}


def _answer(client, headers, topic="obj-case"):
    issued = client.post("/api/practice", headers=headers,
                         json={"topic": topic, "count": 1})
    assert issued.status_code == 200, issued.text
    item = issued.json()["items"][0]
    response = client.post("/api/practice/answer", headers=headers, json={
        "topic": topic, "prompt": "", "answer": "", "given": item["answer"],
        "token": item["token"], "latency_ms": 1000,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _learner_paths():
    return [Path(getattr(config, name)) for name in
            ("PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB", "EVENTS_DB")]


def _state(path: Path):
    return (path.exists(), path.read_bytes() if path.exists() else b"")


def test_a_guest_answer_changes_no_owner_database(client):
    _answer(client, {})
    before = {path: _state(path) for path in _learner_paths()}
    _answer(client, GUEST)
    assert {path: _state(path) for path in before} == before
    with sqlite3.connect(Path(config.GUEST_DIR, "t1", "events.db")) as log:
        rows = log.execute("SELECT learner FROM events WHERE type='attempt'").fetchall()
    assert rows and all(row[0] == "guest:t1" for row in rows)


def test_owner_and_guest_see_their_own_progress(client):
    _answer(client, {}, "obj-case")
    _answer(client, GUEST, "olevik")
    owner = client.get("/api/me", headers={"x-eesti-scope": "owner"}).json()
    guest_profile = client.get("/api/me", headers=GUEST).json()
    assert owner["totals"]["attempts"] == 1
    assert guest_profile["totals"]["attempts"] == 1
    assert owner["scope"] == "owner" and guest_profile["scope"] == "guest"
    assert guest_profile["sandbox"] == "t1"
    # The event topics prove each response came from its own log.
    with sqlite3.connect(config.EVENTS_DB) as log:
        assert log.execute("SELECT learner FROM events WHERE type='attempt'").fetchone()[0] == "owner"
    with sqlite3.connect(Path(config.GUEST_DIR, "t1", "events.db")) as log:
        assert log.execute("SELECT learner FROM events WHERE type='attempt'").fetchone()[0] == "guest:t1"


def test_two_sandboxes_do_not_see_each_other(client):
    a = {"x-eesti-scope": "guest", "x-eesti-guest": "a"}
    b = {"x-eesti-scope": "guest", "x-eesti-guest": "b"}
    _answer(client, a)
    assert client.get("/api/me", headers=a).json()["totals"]["attempts"] == 1
    assert client.get("/api/me", headers=b).json()["totals"]["attempts"] == 0
    _answer(client, b)
    assert client.get("/api/me", headers=b).json()["totals"]["attempts"] == 1
    assert client.get("/api/me", headers=a).json()["totals"]["attempts"] == 1


def test_a_new_guest_is_issued_a_sandbox_cookie(client, monkeypatch):
    monkeypatch.setenv("EESTI_SCOPE", "guest")
    first = client.get("/api/me")
    assert first.status_code == 200
    cookie = first.cookies.get("eesti_guest")
    assert cookie and first.json()["sandbox"] == cookie
    assert "httponly" in first.headers["set-cookie"].lower()
    again = client.get("/api/me")
    assert again.json()["sandbox"] == cookie
    assert "set-cookie" not in again.headers


def test_guest_responses_carry_no_events_seq(client):
    response = client.get("/api/me", headers=GUEST)
    assert response.status_code == 200
    assert "x-events-seq" not in response.headers
    assert client.get("/api/me", headers={"x-eesti-scope": "owner"}).headers.get("x-events-seq") == "0"


def test_the_guest_log_needs_no_restore(client, monkeypatch):
    monkeypatch.setenv("EESTI_WORKER_RESTORES", "1")
    issued = client.post("/api/practice", headers=GUEST,
                         json={"topic": "obj-case", "count": 1}).json()["items"][0]
    response = client.post("/api/practice/answer", headers=GUEST, json={
        "topic": "obj-case", "prompt": "", "answer": "", "given": issued["answer"],
        "token": issued["token"],
    })
    assert response.status_code == 200, response.text
    owner_item = client.post("/api/practice", json={"topic": "obj-case", "count": 1}).json()["items"][0]
    owner_write = client.post("/api/practice/answer", json={
        "topic": "obj-case", "prompt": "", "answer": "", "given": owner_item["answer"],
        "token": owner_item["token"],
    })
    assert owner_write.status_code == 503


def test_the_snapshot_and_export_routes_carry_only_the_owner(client, monkeypatch):
    monkeypatch.setenv("STATE_TOKEN", "state-secret")
    _answer(client, {})
    _answer(client, GUEST)
    owner_headers = {"x-state-token": "state-secret", "x-eesti-scope": "owner"}
    snapshot = client.get("/api/state/export", headers=owner_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["rows"]["progress"] == 1
    events = client.get("/api/events", headers=owner_headers)
    assert events.status_code == 200
    assert {event["learner"] for event in events.json()["events"]} == {"owner"}
    assert client.get("/api/events", headers=STATE | {"x-eesti-guest": "t1"}).status_code == 403


def test_a_guest_sees_the_same_modes_and_source_credits_as_the_owner(client):
    owner_modes = client.get("/api/modes").json()
    guest_modes = client.get("/api/modes", headers=GUEST).json()
    assert [m["id"] for m in guest_modes["modes"]] == [m["id"] for m in owner_modes["modes"]]
    owner_sources = client.get("/api/sources").json()
    guest_sources = client.get("/api/sources", headers=GUEST).json()
    assert guest_sources == owner_sources


def test_every_route_is_classified(client):
    from eesti import api

    docs = (Path(__file__).resolve().parents[1] / "docs" / "identity.md").read_text()
    section = docs.split("## Routes by scope", 1)[1].split("## Guest sandboxes", 1)[0]
    listed = re.findall(r"`(/[^`]*)`", section)
    documented = set(listed)
    routes = set(api.paths())
    assert len(listed) == len(documented), "one route appears in more than one scope row"
    assert documented == routes, (
        f"missing from identity table: {sorted(routes - documented)}; "
        f"stale in identity table: {sorted(documented - routes)}")


def test_the_back_channel_refuses_guest_scope(client, monkeypatch):
    monkeypatch.setenv("STATE_TOKEN", "state-secret")
    for path in ("/api/state/export", "/api/events", "/api/reminders"):
        response = client.get(path, headers=STATE)
        assert response.status_code == 403, (path, response.text)


def test_guest_allowances_are_shared_and_smaller(client):
    from eesti.providers import budget

    a = identity.Scope(kind="guest", id="a")
    b = identity.Scope(kind="guest", id="b")
    with identity.use(a):
        assert budget.left("llm:workers-ai") == budget.GUEST_CAPS["llm:workers-ai"]
        budget.spend("llm:workers-ai", budget.GUEST_CAPS["llm:workers-ai"])
        assert budget.left("llm:workers-ai") == 0
    with identity.use(b):
        assert budget.left("llm:workers-ai") == 0
    with identity.use(identity.OWNER_SCOPE):
        assert budget.left("llm:workers-ai") == budget.CAPS["llm:workers-ai"]
    assert budget.GUEST_CAPS["tartunlp"] < budget.CAPS["tartunlp"]
    assert budget.GUEST_CAPS["tartunlp-mt"] < budget.CAPS["tartunlp-mt"]
    assert budget.GUEST_CAPS["asr:workers-ai"] < budget.CAPS["asr:workers-ai"]


def test_guest_reset_empties_the_sandbox_and_refuses_the_owner(client):
    _answer(client, GUEST)
    assert client.post("/api/guest/reset", headers=GUEST).status_code == 200
    after = client.get("/api/me", headers=GUEST).json()
    assert after["totals"]["attempts"] == 0 and after["name"] is None
    owner = client.post("/api/guest/reset")
    assert owner.status_code == 403


def test_account_removal_deletes_only_the_named_learner_directory(
        client, monkeypatch, tmp_path):
    root = tmp_path / "learners"
    target = root / "l-0123456789abcdef"
    neighbour = root / "l-fedcba9876543210"
    target.mkdir(parents=True)
    neighbour.mkdir()
    (target / "progress.db").write_text("private", encoding="utf-8")
    (neighbour / "progress.db").write_text("keep", encoding="utf-8")
    monkeypatch.setattr(config, "LEARNERS_DIR", str(root))
    monkeypatch.setenv("STATE_TOKEN", "state-secret")

    response = client.post(
        "/api/state/remove-account",
        headers={"x-state-token": "state-secret"},
        json={"id": "l-0123456789abcdef"},
    )
    assert response.status_code == 200
    assert not target.exists()
    assert (neighbour / "progress.db").read_text(encoding="utf-8") == "keep"

    malformed = client.post(
        "/api/state/remove-account",
        headers={"x-state-token": "state-secret"},
        json={"id": "../owner"},
    )
    assert malformed.status_code == 400
    refused = client.post(
        "/api/state/remove-account",
        headers={
            "x-state-token": "state-secret",
            "x-eesti-scope": "learner",
            "x-eesti-learner": "l-fedcba9876543210",
        },
        json={"id": "l-fedcba9876543210"},
    )
    assert refused.status_code == 403
    assert neighbour.exists()


def test_progress_reset_refuses_guests_without_changing_their_sandbox(client):
    _answer(client, GUEST)
    response = client.post("/api/me/reset", headers=GUEST, json={})
    assert response.status_code == 403
    restore = client.post("/api/me/restore", headers=GUEST, json={})
    assert restore.status_code == 403
    assert client.get("/api/me", headers=GUEST).json()["totals"]["attempts"] == 1


def _sandboxes(root, ages):
    """Sandbox folders whose `last-used` is `ages[name]` seconds old."""
    import os

    now = time.time()
    for name, age in ages.items():
        folder = root / name
        folder.mkdir()
        (folder / "last-used").touch()
        os.utime(folder / "last-used", (now - age, now - age))


def test_idle_and_surplus_sandboxes_are_swept(tmp_path, monkeypatch):
    """Over the soft limit, only a sandbox idle for an hour may go: a burst of
    new visitors must not erase a guest who is mid-session."""
    root = tmp_path / "guest"
    root.mkdir()
    monkeypatch.setattr(config, "GUEST_DIR", str(root))
    surplus = 3
    ages = {"idle": 25 * 60 * 60}
    ages |= {f"quiet{i}": 2 * 60 * 60 + i for i in range(surplus)}
    ages |= {f"busy{i:02d}": i for i in range(guest.MAX_SANDBOXES)}
    _sandboxes(root, ages)
    removed = guest.sweep()
    assert sorted(removed) == ["idle", *(f"quiet{i}" for i in range(surplus))]
    assert all((root / f"busy{i:02d}").exists() for i in range(guest.MAX_SANDBOXES))


def test_a_burst_of_active_guests_keeps_every_sandbox(tmp_path, monkeypatch):
    root = tmp_path / "guest"
    root.mkdir()
    monkeypatch.setattr(config, "GUEST_DIR", str(root))
    _sandboxes(root, {f"s{i:03d}": i for i in range(guest.MAX_SANDBOXES + 20)})
    assert guest.sweep() == []


def test_the_hard_limit_still_bounds_the_disk(tmp_path, monkeypatch):
    """Cloud Run's disk is memory: past the hard limit the longest-idle goes."""
    root = tmp_path / "guest"
    root.mkdir()
    monkeypatch.setattr(config, "GUEST_DIR", str(root))
    _sandboxes(root, {f"s{i:03d}": i for i in range(guest.HARD_MAX_SANDBOXES + 2)})
    removed = guest.sweep()
    oldest = [f"s{i:03d}" for i in (guest.HARD_MAX_SANDBOXES + 1, guest.HARD_MAX_SANDBOXES)]
    assert sorted(removed) == sorted(oldest)


def test_guest_allowances_survive_a_cold_start(client, monkeypatch):
    """A cold start empties the guest directory; if it also emptied the guest
    allowance, every restart would hand guests a fresh day of the account's
    shared Workers AI neurons. The count travels in the owner's snapshot."""
    import base64
    import shutil
    import sqlite3

    from eesti.providers import budget

    with identity.use(identity.Scope(kind="guest", id="a")):
        budget.spend("llm:workers-ai", 7)
    shutil.rmtree(config.GUEST_DIR, ignore_errors=True)
    with identity.use(identity.Scope(kind="guest", id="b")):
        assert budget.spent("llm:workers-ai") == 7
    with identity.use(identity.OWNER_SCOPE):
        assert budget.spent("llm:workers-ai") == 0

    monkeypatch.setenv("STATE_TOKEN", "state-secret")
    snapshot = client.get("/api/state/export", headers={"x-state-token": "state-secret"}
                          ).json()["databases"]["progress"]
    with sqlite3.connect(":memory:") as conn:
        conn.deserialize(base64.b64decode(snapshot))
        rows = dict(conn.execute("SELECT lane, calls FROM budget"))
    assert rows.get("guest:llm:workers-ai") == 7
