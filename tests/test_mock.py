"""The timed mock: the exam's clock and shape over the app's own material.

It is not a copy of HARNO's paper, and each section says so. Only what code can
decide is graded; speaking is recorded and never scored.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import config, evidence, mock  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)


def _progress():
    from eesti import progress

    return progress.connect(config.PROGRESS_DB)


class TestTheSections:
    @pytest.mark.parametrize("part,kind,minutes", [
        ("lugemine", "cloze", 50), ("kuulamine", "dictation", 30),
        ("kirjutamine", "writing", 30), ("raakimine", "speaking", 15)])
    def test_each_part_runs_on_the_exam_s_own_clock(self, client, part, kind, minutes):
        body = client.get(f"/api/mock/A2/{part}?seed=1").json()
        assert body["kind"] == kind and body["minutes"] == minutes
        assert body["tasks"] and body["note"]
        # The exam's own name for the part, not the database key.
        from eesti.exam import SPECS

        assert body["et"] == SPECS["A2"].part(part).et

    def test_the_same_seed_builds_the_same_section(self, client):
        one = client.get("/api/mock/A2/lugemine?seed=7").json()
        two = client.get("/api/mock/A2/lugemine?seed=7").json()
        assert [t["prompt"] for t in one["tasks"]] == [t["prompt"] for t in two["tasks"]]

    def test_a_reading_task_regenerates_from_its_token(self, client):
        from eesti.itemref import regenerate, verify

        task = client.get("/api/mock/A2/lugemine?seed=3").json()["tasks"][0]
        again = regenerate(verify(task["token"])["ref"])
        assert (again.prompt, again.answer) == (task["prompt"], task["answer"])

    def test_an_unknown_part_or_level_is_a_404(self, client):
        assert client.get("/api/mock/A2/joonistamine").status_code == 404
        assert client.get("/api/mock/C1/lugemine").status_code == 404


class TestGrading:
    def test_reading_is_graded_from_the_tokens_the_server_issued(self, client):
        section = client.get("/api/mock/A2/lugemine?seed=5").json()
        answers = [{"token": t["token"], "given": t["answer"] if n % 2 else "vale"}
                   for n, t in enumerate(section["tasks"])]
        got = client.post("/api/mock/A2/lugemine",
                          json={"seconds": 900, "answers": answers}).json()
        assert got["asked"] == len(answers)
        assert got["correct"] == sum(1 for n in range(len(answers)) if n % 2)

    def test_a_forged_reading_token_is_refused(self, client):
        section = client.get("/api/mock/A2/lugemine?seed=5").json()
        body, mac = section["tasks"][0]["token"].rsplit(".", 1)
        r = client.post("/api/mock/A2/lugemine", json={
            "seconds": 10, "answers": [{"token": body + "." + "0" * len(mac),
                                        "given": "x"}]})
        assert r.status_code == 400

    def test_dictation_is_graded_word_by_word(self, client):
        section = client.get("/api/mock/A2/kuulamine?seed=2").json()
        answers = [{"text": t["text"], "given": t["text"]} for t in section["tasks"]]
        got = client.post("/api/mock/A2/kuulamine",
                          json={"seconds": 600, "answers": answers}).json()
        assert got["correct"] == len(answers)

    def test_writing_counts_words_against_harno_s_minimum(self, client):
        short = client.post("/api/mock/A2/kirjutamine",
                            json={"seconds": 300, "written": "Tere. Ma olen siin."}).json()
        assert short["correct"] == 0 and short["detail"]["min_words"] == mock.MIN_WORDS["A2"]
        long = client.post("/api/mock/A2/kirjutamine", json={
            "seconds": 300, "written": " ".join(["sõna"] * 40)}).json()
        assert long["correct"] == 1 and long["detail"]["words"] == 40

    def test_speaking_is_recorded_and_never_scored(self, client):
        got = client.post("/api/mock/A2/raakimine",
                          json={"seconds": 600, "answers": [{"given": ""}]}).json()
        assert got["correct"] is None and got["asked"] == 1


class TestEvidence:
    def test_a_section_is_evidence_for_its_part(self, client):
        before = client.get("/api/readiness/A2").json()
        assert next(p for p in before["parts"] if p["id"] == "kuulamine")["touched"] is False
        section = client.get("/api/mock/A2/kuulamine?seed=2").json()
        client.post("/api/mock/A2/kuulamine", json={
            "seconds": 300,
            "answers": [{"text": t["text"], "given": t["text"]} for t in section["tasks"]]})
        after = client.get("/api/readiness/A2").json()
        part = next(p for p in after["parts"] if p["id"] == "kuulamine")
        assert part["touched"] is True and "на время" in part["evidence"]

    def test_sections_survive_a_replay(self, client):
        client.post("/api/mock/A2/kirjutamine",
                    json={"seconds": 120, "written": " ".join(["sõna"] * 40)})
        with evidence.connect() as log:
            assert [e.type for e in evidence.events(log)][-1] == "exam-section"
            evidence.rebuild(log)
        assert mock.counts(_progress(), "A2") == {"kirjutamine": 1}

    def test_the_history_is_served(self, client):
        client.post("/api/mock/A2/raakimine", json={"seconds": 60, "answers": []})
        body = client.get("/api/mock/A2").json()
        assert body["counts"] == {"raakimine": 1}
        assert body["sections"][0]["seconds"] == 60
