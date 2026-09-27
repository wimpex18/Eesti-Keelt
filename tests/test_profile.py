"""The profile (ADR-0006, `docs/identity.md` "Profile")."""

from __future__ import annotations

import json

from eesti import config, evidence


def test_an_empty_log_is_a_profile_with_nothing_yet(client):
    response = client.get("/api/me")
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "scope", "sandbox", "name", "email", "since", "last_active",
        "active_days_28", "level", "milestones", "totals", "rhythm",
    }
    assert body["scope"] == "owner" and body["sandbox"] is None
    assert body["name"] is body["email"] is body["since"] is body["last_active"] is None
    assert body["active_days_28"] == 0
    assert body["totals"]["attempts"] == body["totals"]["mastered"] == 0
    assert body["totals"]["review_cards"] == body["totals"]["known_words"] == 0
    assert body["totals"]["topics"] > 0
    assert len(body["rhythm"]) == 84
    assert body["level"] == {"current": "A1", "goal": None, "checkpoints": []}
    assert set(body["milestones"]) == {"A1", "A2", "B1"}


def test_the_name_is_set_trimmed_and_read_back(client):
    response = client.post("/api/me", json={"name": "  Sergey   Z "})
    assert response.status_code == 200
    assert response.json()["name"] == "Sergey Z"
    assert client.get("/api/me").json()["name"] == "Sergey Z"
    with evidence.connect() as log:
        event = log.execute(
            "SELECT type,payload FROM events WHERE type='profile-set'"
        ).fetchone()
    assert event["type"] == "profile-set"
    assert json.loads(event["payload"]) == {"name": "Sergey Z"}


def test_a_blank_name_clears_it_and_a_long_one_is_refused(client):
    assert client.post("/api/me", json={"name": "Sergey"}).status_code == 200
    assert client.post("/api/me", json={"name": "  "}).json()["name"] is None
    response = client.post("/api/me", json={"name": "x" * 61})
    assert response.status_code == 400
    assert any("Ѐ" <= ch <= "ӿ" for ch in response.json()["detail"])


def test_profile_set_survives_strict_replay(client, tmp_path):
    """Strict replay accepts the event type and can replay it twice."""
    from eesti import recovery

    assert client.post("/api/me", json={"name": "Replay"}).status_code == 200
    backup = tmp_path / "events.jsonl"
    backup.write_text(client.get("/api/me/export").text, encoding="utf-8")
    assert recovery.verify_export(backup)["verified"] is True


def test_the_email_comes_from_the_front_door(client, monkeypatch):
    monkeypatch.setenv("PROXY_TOKEN", "proxy-secret")
    owner = client.get("/api/me", headers={
        "x-proxy-token": "proxy-secret", "x-eesti-scope": "owner",
        "x-eesti-email": " owner@example.test ",
    })
    assert owner.status_code == 200 and owner.json()["email"] == "owner@example.test"
    learner = client.get("/api/me", headers={
        "x-proxy-token": "proxy-secret", "x-eesti-scope": "learner",
        "x-eesti-learner": "l-0123456789abcdef", "x-eesti-email": "her@example.test",
    })
    assert learner.status_code == 200
    assert learner.json()["scope"] == "learner"
    assert learner.json()["email"] == "her@example.test"
    without = client.get("/api/me", headers={
        "x-proxy-token": "proxy-secret", "x-eesti-scope": "owner",
    })
    assert without.status_code == 200 and without.json()["email"] is None


def test_level_milestones_and_rhythm_match_their_own_routes(client):
    item = client.post("/api/practice", json={
        "topic": "obj-case", "count": 1,
    }).json()["items"][0]
    answer = client.post("/api/practice/answer", json={
        "topic": "obj-case", "prompt": "", "answer": "", "given": item["answer"],
        "token": item["token"], "latency_ms": 1200,
    })
    assert answer.status_code == 200, answer.text
    me = client.get("/api/me").json()
    assert me["level"]["current"] is not None
    assert me["milestones"]["A1"] == client.get("/api/milestones/A1").json()["milestones"]
    assert me["rhythm"] == client.get("/api/status").json()["rhythm"]
    assert me["active_days_28"] == sum(day["n"] > 0 for day in me["rhythm"][-28:])
    assert me["last_active"] is not None
