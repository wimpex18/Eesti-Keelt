"""The profile (ADR-0006, `docs/identity.md` "Profile")."""

from __future__ import annotations

import json

from eesti import evidence


def test_an_empty_log_is_a_profile_with_nothing_yet(client):
    response = client.get("/api/me")
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "scope", "sandbox", "name", "email", "since", "last_active",
        "active_days_28", "level", "milestones", "totals", "rhythm",
        "restore_available", "restore_at",
    }
    assert body["scope"] == "owner" and body["sandbox"] is None
    assert body["name"] is body["email"] is body["since"] is body["last_active"] is None
    assert body["active_days_28"] == 0
    assert body["totals"]["attempts"] == body["totals"]["mastered"] == 0
    assert body["totals"]["review_cards"] == body["totals"]["known_words"] == 0
    assert body["totals"]["topics"] > 0
    assert len(body["rhythm"]) == 84
    assert body["restore_available"] is False and body["restore_at"] is None
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


def test_reset_clears_every_projection_and_preserves_the_profile(client, tmp_path):
    """The reset marker survives replay without deleting account identity."""
    from eesti import review

    stamp = "2026-01-02T12:00:00+00:00"
    stores = evidence.Stores()
    try:
        progress = stores["progress"]
        with progress:
            progress.execute(
                "INSERT INTO attempts (topic,item_key,correct,answer,at,rule)"
                " VALUES (?,?,?,?,?,?)",
                ("obj-case", "seed", 1, "raamatu", stamp, None))
            progress.execute(
                "INSERT INTO topic_state (topic,mastered_at,via,last_seen)"
                " VALUES (?,?,?,?)", ("obj-case", stamp, "practice", stamp))
            progress.execute(
                "INSERT INTO checkpoints (level,asked,correct,passed,at)"
                " VALUES (?,?,?,?,?)", ("A1", 10, 10, 1, stamp))
            progress.execute(
                "INSERT INTO dictation (key,text,typed,matched,total,correct,at)"
                " VALUES (?,?,?,?,?,?,?)", ("d1", "tere", "tere", 1, 1, 1, stamp))
            progress.execute(
                "INSERT INTO exposure (item_id,seen_at,minutes) VALUES (?,?,?)",
                ("text-1", stamp, 2))
            progress.execute(
                "INSERT INTO goal (id,level,sitting,registration_closes,set_at)"
                " VALUES (1,'A2','2026-10-01',NULL,?)", (stamp,))
            progress.execute(
                "INSERT INTO exam_sections (level,part,seconds,asked,correct,at,detail)"
                " VALUES ('A2','lugemine',60,1,1,?,NULL)", (stamp,))
        reviews = stores["review"]
        with reviews:
            reviews.execute(
                "INSERT INTO review_items (id,kind,lemma,prompt,answer,card,due)"
                " VALUES ('r1','obj-case','raamat','Ostan ___.','raamatu','{}',?)",
                (stamp,))
        vocabulary = stores["vocab"]
        with vocabulary:
            vocabulary.execute(
                "INSERT INTO vocab_status (lemma,status,met_count,first_seen,last_seen)"
                " VALUES ('raamat',5,1,?,?)", (stamp, stamp))
        notion = stores["notion"]
        with notion:
            notion.execute(
                "INSERT INTO notion_queue (wrong,correct,why,tag,on_date,pushed)"
                " VALUES ('raamatu','raamatu','ok','obj-case','2026-01-02',NULL)")
    finally:
        stores.close()

    assert client.post("/api/me", json={"name": "Aino Tamm"}).status_code == 200
    before = client.get("/api/me").json()
    assert before["totals"]["attempts"] == 1
    assert before["totals"]["review_cards"] == before["totals"]["known_words"] == 1
    with evidence.connect() as log:
        evidence.record("fsrs-parameters", {"parameters": [0.1, 0.2]})
    assert review.parameters() == (0.1, 0.2)

    response = client.post("/api/me/reset", json={})
    assert response.status_code == 200, response.text
    assert response.json()["reset"] is True
    after = client.get("/api/me").json()
    assert after["name"] == before["name"] == "Aino Tamm"
    assert after["since"] == before["since"]
    assert after["last_active"] is None and after["active_days_28"] == 0
    assert after["level"] == {"current": "A1", "goal": None, "checkpoints": []}
    assert after["totals"]["attempts"] == after["totals"]["mastered"] == 0
    assert after["totals"]["review_cards"] == after["totals"]["known_words"] == 0
    assert not any(day["n"] for day in after["rhythm"])
    assert after["restore_available"] is True and after["restore_at"]
    assert review.parameters() is None

    with evidence.connect() as log:
        assert log.execute(
            "SELECT 1 FROM events WHERE type=?", ("profile-progress-reset",)
        ).fetchone()
        assert evidence.rebuild(log) > 0
        from eesti import recovery

        backup = tmp_path / "profile-reset-events.jsonl"
        backup.write_text(client.get("/api/me/export").text, encoding="utf-8")
        assert recovery.verify_export(backup)["verified"] is True
        backup.unlink()
    replayed = evidence.Stores()
    try:
        for database, tables in evidence.PROJECTIONS.items():
            for table in tables:
                assert replayed[database].execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    finally:
        replayed.close()

    item = client.post("/api/practice", json={"topic": "obj-case", "count": 1}).json()["items"][0]
    answer = client.post("/api/practice/answer", json={
        "topic": "obj-case", "prompt": "", "answer": "", "given": item["answer"],
        "token": item["token"], "latency_ms": 1200,
    })
    assert answer.status_code == 200, answer.text

    restored = client.post("/api/me/restore", json={})
    assert restored.status_code == 200, restored.text
    assert restored.json()["restored"] is True
    recovered = client.get("/api/me").json()
    assert recovered["name"] == before["name"] == "Aino Tamm"
    assert recovered["since"] == before["since"]
    assert recovered["level"]["goal"] == before["level"]["goal"]
    assert recovered["totals"]["attempts"] == 2  # old history plus post-reset practice
    assert recovered["totals"]["review_cards"] == recovered["totals"]["known_words"] == 1
    assert recovered["restore_available"] is False and recovered["restore_at"] is None
    assert review.parameters() == (0.1, 0.2)

    with evidence.connect() as log:
        assert log.execute(
            "SELECT 1 FROM events WHERE type=?", ("profile-progress-restored",)
        ).fetchone()
        assert evidence.rebuild(log, strict=True) > 0
        backup = tmp_path / "profile-restored-events.jsonl"
        backup.write_text(client.get("/api/me/export").text, encoding="utf-8")
        assert recovery.verify_export(backup)["verified"] is True
        backup.unlink()

    assert client.post("/api/me/reset", json={}).status_code == 200
    assert client.get("/api/me").json()["restore_available"] is True
    assert client.post("/api/me/restore", json={}).status_code == 200
    assert client.get("/api/me").json()["totals"]["attempts"] == 2


def test_progress_reset_is_available_to_a_learner_account(client, monkeypatch):
    monkeypatch.setenv("PROXY_TOKEN", "proxy-secret")
    headers = {
        "x-proxy-token": "proxy-secret", "x-eesti-scope": "learner",
        "x-eesti-learner": "l-0123456789abcdef", "x-eesti-email": "her@example.test",
    }
    response = client.post("/api/me/reset", headers=headers, json={})
    assert response.status_code == 200, response.text
    restored = client.post("/api/me/restore", headers=headers, json={})
    assert restored.status_code == 200, restored.text


def test_restore_refuses_when_no_reset_point_exists(client):
    response = client.post("/api/me/restore", json={})
    assert response.status_code == 409
    assert client.get("/api/me").json()["restore_available"] is False
