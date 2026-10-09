"""Fast-forward must remain reversible navigation, including after replay."""

from eesti import evidence


def test_topic_skip_moves_course_without_assessed_evidence(client):
    initial = client.get("/api/curriculum").json()
    topic = initial["resume"]
    response = client.post(f"/api/course/topics/{topic}/skip", json={"skip": True})
    assert response.status_code == 200
    moved = response.json()
    assert moved["resume"] != topic
    row = next(row for row in moved["topics"] if row["id"] == topic)
    assert row["state"] == "skipped" and row["attempts"] == 0
    profile = client.get("/api/me").json()
    assert profile["totals"]["mastered"] == profile["totals"]["review_cards"] == 0
    assert profile["totals"]["attempts"] == 0
    with evidence.connect() as log:
        evidence.rebuild(log, strict=True)
    assert client.get("/api/curriculum").json()["resume"] == moved["resume"]
    restored = client.post(f"/api/course/topics/{topic}/skip", json={"skip": False})
    assert restored.json()["resume"] == topic


def test_selected_start_can_change_without_erasing_manual_skips(client):
    initial = client.get("/api/curriculum").json()
    manual = initial["resume"]
    assert client.post(f"/api/course/topics/{manual}/skip", json={}).status_code == 200
    assert client.post("/api/me/onboarding", json={
        "start_band": "a2", "focus": "path", "navigate": True,
        "explanation_language": "ru",
    }).status_code == 200
    route = client.get("/api/curriculum").json()
    next_topic = next(row for row in route["topics"] if row["id"] == route["resume"])
    assert next_topic["level"] == "A2"
    assert route["mastered"] == 0
    with evidence.connect() as log:
        evidence.rebuild(log, strict=True)
    assert client.get("/api/curriculum").json()["resume"] == route["resume"]
    client.post("/api/me/onboarding", json={
        "start_band": "a0", "focus": "path", "navigate": True,
    })
    rows = client.get("/api/curriculum").json()["topics"]
    assert {row["id"] for row in rows if row["skipped"]} == {manual}


def test_old_preferences_do_not_silently_skip_and_unknown_topics_fail(client):
    initial = client.get("/api/curriculum").json()["resume"]
    client.post("/api/me/onboarding", json={"start_band": "a2", "focus": "path"})
    assert client.get("/api/curriculum").json()["resume"] == initial
    assert client.post("/api/course/topics/not-a-topic/skip", json={}).status_code == 404


def test_grammar_entry_assessment_does_not_award_a_pass_from_client_history(client):
    first = client.get("/api/placement/next").json()
    assert first["next"]["items"] and not first["done"]
    topic = first["next"]["topic"]
    finished = client.get(f"/api/placement/next?seen={topic}&failed={topic}&limit=1").json()
    assert finished["done"] and finished["entry"]["id"] == topic
    assert client.get("/api/me").json()["totals"]["mastered"] == 0
    assert client.get("/api/me").json()["totals"]["attempts"] == 0


def test_starter_sentences_are_generated_without_recording_attempts(client):
    result = client.get("/api/learning/sentences").json()
    assert result["sentences"] and result["source_id"] == "generated"
    assert all("____" not in sentence for sentence in result["sentences"])
    assert result["reference"]["url"]
    assert client.get("/api/me").json()["totals"]["attempts"] == 0


def test_empty_imported_corpus_still_offers_listening_and_readaloud(client, monkeypatch):
    from eesti import dictation, pronunciation
    from eesti.api import speech

    monkeypatch.setattr(speech, "_human_passages", lambda *args: [])
    monkeypatch.setattr(dictation, "choose", lambda *args, **kwargs: [])
    monkeypatch.setattr(pronunciation, "sentences_to_say", lambda *args, **kwargs: [])
    listening = client.get("/api/dictation/next").json()
    assert listening["starter"] and listening["passages"]
    assert all(item["source"] == "generated" for item in listening["passages"])
    speaking = client.get("/api/speaking/readaloud").json()
    assert speaking["items"]
    assert all(item["source"] == "generated" for item in speaking["items"])
    assert client.get("/api/me").json()["totals"]["attempts"] == 0


def test_local_account_capability_does_not_advertise_worker_signup(client):
    result = client.get("/api/auth/me")
    assert result.status_code == 200
    assert result.json() == {"scope": "owner", "signup_open": False, "local": True}


def test_a_run_of_units_is_skipped_and_restored_without_assessed_evidence(client):
    """'Start from unit 3': the learner moves past units 1–2 in one step, and can
    put either back. Nothing is mastered, and replay keeps the choice."""
    first = client.get("/api/curriculum").json()
    before = [u["id"] for u in first["units"][:2]]
    moved = client.post("/api/course/units/skip", json={"units": before, "skip": True})
    assert moved.status_code == 200
    route = moved.json()
    units = {u["id"]: u for u in route["units"]}
    assert all(units[u]["skipped"] for u in before)
    skipped_topics = {t for u in before for t in units[u]["topics"]}
    states = {row["id"]: row["state"] for row in route["topics"]}
    assert {states[t] for t in skipped_topics} == {"skipped"}
    assert route["resume"] not in skipped_topics
    assert client.get("/api/me").json()["totals"]["mastered"] == 0
    with evidence.connect() as log:
        evidence.rebuild(log, strict=True)
    assert client.get("/api/curriculum").json()["resume"] == route["resume"]

    back = client.post("/api/course/units/skip", json={"units": before[1:], "skip": False}).json()
    units = {u["id"]: u for u in back["units"]}
    assert units[before[0]]["skipped"] and not units[before[1]]["skipped"]


def test_an_unknown_unit_is_refused_and_records_nothing(client):
    r = client.post("/api/course/units/skip", json={"units": ["no-such-unit"], "skip": True})
    assert r.status_code == 404
    assert not any(row["skipped"] for row in client.get("/api/curriculum").json()["topics"])
