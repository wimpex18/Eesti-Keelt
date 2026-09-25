"""Read-aloud sentences the learner confirms become a measurement of the
recogniser; a planted wrong form tells whether it repairs mistakes away.
"""

from __future__ import annotations

import pytest

from eesti.asrcheck import MIN_PROBES, MIN_SENTENCES, score

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)


class TestScore:
    def test_a_repaired_planted_form_is_named(self):
        s = score("Ma leidsin rahakotti üles.", "ma leidsin rahakoti üles",
                  index=2, planted="rahakotti", correct="rahakoti")
        assert s["probe"] == "repaired" and s["errors"] == 1

    def test_a_kept_planted_form_is_no_error(self):
        s = score("Ma leidsin rahakotti üles.", "Ma leidsin rahakotti üles.",
                  index=2, planted="rahakotti", correct="rahakoti")
        assert s == {"words": 4, "errors": 0, "probe": "kept", "heard": "rahakotti"}

    def test_an_added_word_counts_as_an_error(self):
        assert score("Tere hommikust", "tere tere hommikust")["errors"] == 1


class TestTheRoutes:
    def _check(self, client, **kw):
        body = {"target": "Ma leidsin rahakotti üles.",
                "transcript": "ma leidsin rahakoti üles", "said": "as-written"} | kw
        return client.post("/api/speaking/check", json=body)

    def test_no_rate_below_the_floors(self, client):
        r = self._check(client, index=2, planted="rahakotti", correct="rahakoti").json()
        assert r["sentences"] == 1 and r["probes"]["repaired"] == 1
        assert r["word_error_rate"] is None and r["false_acceptance"] is None

    def test_rates_past_the_floors(self, client):
        for _ in range(MIN_SENTENCES - MIN_PROBES):
            self._check(client, transcript="Ma leidsin rahakotti üles.")
        for _ in range(MIN_PROBES):
            r = self._check(client, index=2, planted="rahakotti", correct="rahakoti").json()
        assert r["false_acceptance"] == 1.0
        assert r["word_error_rate"] == round(MIN_PROBES / (4 * MIN_SENTENCES), 3)

    def test_a_misread_sentence_is_not_scored(self, client):
        r = self._check(client, said="differently").json()
        assert r["sentences"] == 0 and r["differently"] == 1

    def test_an_unknown_answer_is_refused(self, client):
        assert self._check(client, said="maybe").status_code == 400

    def test_a_probe_is_offered(self, client):
        r = client.get("/api/speaking/probe", params={"seed": 1})
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            p = r.json()
            assert p["planted"] in p["text"] and p["planted"] != p["correct"]
