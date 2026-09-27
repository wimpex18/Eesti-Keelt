"""Permanent learner accounts have separate logs, projections and back channels."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from eesti import config, identity

HER = {"x-eesti-scope": "learner", "x-eesti-learner": "l-0123456789abcdef",
       "x-eesti-email": "her@example.com"}
HIM = {"x-eesti-scope": "learner", "x-eesti-learner": "l-fedcba9876543210",
       "x-eesti-email": "him@example.com"}
STATE = {"x-state-token": "state-secret"}


def _answer(client, headers, *, correct=False):
    issued = client.post("/api/practice", headers=headers,
                         json={"topic": "obj-case", "count": 1})
    assert issued.status_code == 200, issued.text
    item = issued.json()["items"][0]
    response = client.post("/api/practice/answer", headers=headers, json={
        "topic": "obj-case", "prompt": "", "answer": "",
        "given": item["answer"] if correct else "not-the-answer",
        "token": item["token"], "latency_ms": 1000,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _owner_headers():
    return {"x-eesti-scope": "owner"}


def test_two_learners_keep_separate_permanent_progress(client):
    _answer(client, _owner_headers())
    _answer(client, HER, correct=True)
    owner = client.get("/api/me", headers=_owner_headers()).json()
    learner = client.get("/api/me", headers=HER).json()
    other = client.get("/api/me", headers=HIM).json()
    assert owner["totals"]["attempts"] == learner["totals"]["attempts"] == 1
    assert other["totals"]["attempts"] == 0
    owner_queue = client.get("/api/review/stats", headers=_owner_headers()).json()
    learner_queue = client.get("/api/review/stats", headers=HER).json()
    other_queue = client.get("/api/review/stats", headers=HIM).json()
    assert owner_queue["total"] >= 1
    assert learner_queue["total"] == other_queue["total"] == 0
    assert learner["email"] == "her@example.com" and learner["scope"] == "learner"
    assert Path(config.LEARNERS_DIR, HER["x-eesti-learner"], "progress.db").exists()
    assert Path(config.LEARNERS_DIR, HIM["x-eesti-learner"], "progress.db").exists()
    with sqlite3.connect(config.PROGRESS_DB) as progress:
        assert progress.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 1
    with sqlite3.connect(Path(config.LEARNERS_DIR, HER["x-eesti-learner"], "progress.db")) as progress:
        assert progress.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 1


def test_a_learner_has_her_own_back_channel(client, monkeypatch):
    monkeypatch.setenv("STATE_TOKEN", "state-secret")
    _answer(client, _owner_headers())
    _answer(client, HER, correct=True)
    owner_headers = STATE | _owner_headers()
    learner_headers = STATE | HER
    owner_snapshot = client.get("/api/state/export", headers=owner_headers).json()
    learner_snapshot = client.get("/api/state/export", headers=learner_headers).json()
    assert owner_snapshot["rows"]["progress"] == learner_snapshot["rows"]["progress"] == 1
    owner_events = client.get("/api/events", headers=owner_headers).json()["events"]
    learner_events = client.get("/api/events", headers=learner_headers).json()["events"]
    assert {event["learner"] for event in owner_events} == {"owner"}
    assert {event["learner"] for event in learner_events} == {HER["x-eesti-learner"]}
    imported = client.post("/api/events/import", headers=learner_headers,
                           json={"events": learner_events}).json()
    assert imported["added"] == 0
    assert client.get("/api/reminders", headers=learner_headers).status_code == 200
    assert client.get("/api/events", headers=owner_headers).json()["events"] == owner_events


def test_a_learner_is_restored_like_the_owner(client, monkeypatch):
    monkeypatch.setenv("STATE_TOKEN", "state-secret")
    monkeypatch.setenv("EESTI_WORKER_RESTORES", "1")
    issued = client.post("/api/practice", headers=HER,
                         json={"topic": "obj-case", "count": 1}).json()["items"][0]
    body = {"topic": "obj-case", "prompt": "", "answer": "",
            "given": issued["answer"], "token": issued["token"]}
    assert client.post("/api/practice/answer", headers=HER, json=body).status_code == 503
    settled = client.post("/api/events/import", headers=STATE | HER,
                          json={"events": [], "settle": True})
    assert settled.status_code == 200
    assert client.post("/api/practice/answer", headers=HER, json=body).status_code == 200


def test_a_new_learner_is_registered_once(client, monkeypatch):
    monkeypatch.setenv("STATE_TOKEN", "state-secret")
    headers = STATE | HER
    first = client.post("/api/events/import", headers=headers,
                        json={"events": [], "settle": True})
    second = client.post("/api/events/import", headers=headers,
                         json={"events": [], "settle": True})
    assert first.status_code == second.status_code == 200
    events = client.get("/api/events", headers=headers).json()["events"]
    joined = [event for event in events if event["type"] == "joined"]
    assert len(joined) == 1
    assert client.get("/api/me", headers=HER).json()["since"] == joined[0]["ts"]


def test_x_events_seq_reports_the_callers_own_log(client):
    client.post("/api/me", headers=_owner_headers(), json={"name": "Owner"})
    client.post("/api/me", headers=HER, json={"name": "Her"})
    client.post("/api/me", headers=HER, json={"name": "Her again"})
    owner = client.get("/api/me", headers=_owner_headers())
    learner = client.get("/api/me", headers=HER)
    assert owner.headers["x-events-seq"] == "2"
    assert learner.headers["x-events-seq"] == "3"


def test_owner_only_actions_are_refused_to_a_learner(client, monkeypatch):
    monkeypatch.setenv("STATE_TOKEN", "state-secret")
    headers = STATE | HER
    requests = [
        client.post("/api/notion/push", headers=HER, json={"ids": [1]}),
        client.get("/api/eval/available", headers=HER),
        client.post("/api/eval/clip", headers=HER, json={}),
        client.post("/api/eval/draft/test", headers=HER, json={}),
        client.post("/api/eval/review/test", headers=HER, json={}),
        client.get("/api/eval/prompt", headers=HER),
        client.post("/api/content/import", headers=headers, json={"database": "eA=="}),
        client.get("/api/content/export", headers=headers),
        client.post("/api/progress/reset", headers=headers,
                    json={"topic": "obj-case"}),
    ]
    for response in requests:
        assert response.status_code == 403, response.text
        assert any("Ѐ" <= char <= "ӿ" for char in response.json()["detail"])


def test_learners_share_the_household_allowance(client):
    from eesti.providers import budget

    learner = identity.Scope(kind="learner", id=HER["x-eesti-learner"])
    with identity.use(learner):
        before = budget.left("llm:workers-ai")
        budget.spend("llm:workers-ai", 1)
        assert budget.left("llm:workers-ai") == before - 1
    with identity.use(identity.OWNER_SCOPE):
        assert budget.left("llm:workers-ai") == before - 1


def test_events_carry_the_learner_id(client):
    _answer(client, HER)
    with sqlite3.connect(Path(config.LEARNERS_DIR, HER["x-eesti-learner"], "events.db")) as log:
        rows = log.execute("SELECT learner FROM events WHERE type='attempt'").fetchall()
    assert rows and all(row[0] == HER["x-eesti-learner"] for row in rows)
