"""Practising with no connection: a set fetched in advance, graded by the same
rule, and re-graded by the server when the answers arrive.
"""

from __future__ import annotations

import uuid

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import evidence  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app

    return TestClient(app)


def _attempts():
    with evidence.connect() as log:
        return [e for e in evidence.events(log) if e.type == "attempt"]


class TestThePack:
    def test_it_carries_items_with_their_answers_and_tokens(self, client):
        pack = client.get("/api/pack?count=8").json()
        assert pack["topics"] and len(pack["items"]) <= 8
        first = pack["items"][0]
        # Offline there is nobody to ask, so the answer travels with the item —
        # and so does the token, which is what the server re-grades from.
        assert first["answer"] and first["token"] and first["topic"]
        assert "записываются" in pack["note"]

    def test_it_is_bounded(self, client):
        assert len(client.get("/api/pack?count=500").json()["items"]) <= 60
        assert len(client.get("/api/pack?count=1").json()["items"]) >= 1


class TestSendingWhatWasAnsweredOffline:
    def _answer(self, client, item, given, event_id, at):
        return client.post("/api/practice/answer", json={
            "topic": item["topic"], "prompt": "", "answer": "", "given": given,
            "token": item["token"], "event_id": event_id, "at": at}).json()

    def test_the_server_regrades_it_and_keeps_the_time_it_happened(self, client):
        item = client.get("/api/pack?count=4").json()["items"][0]
        when = "2026-09-18T20:15:00+00:00"
        got = self._answer(client, item, item["answer"], str(uuid.uuid7()), when)
        assert got["correct"] is True
        assert _attempts()[-1].ts == when

    def test_the_page_cannot_mark_its_own_answer_right(self, client):
        """The page grades offline so it can show a verdict; the server decides."""
        item = client.get("/api/pack?count=4").json()["items"][0]
        got = self._answer(client, item, "ilmselgelt vale", str(uuid.uuid7()),
                           "2026-09-18T20:16:00+00:00")
        assert got["correct"] is False

    def test_sending_the_queue_twice_records_once(self, client):
        item = client.get("/api/pack?count=4").json()["items"][0]
        event_id, when = str(uuid.uuid7()), "2026-09-18T20:17:00+00:00"
        before = len(_attempts())
        first = self._answer(client, item, item["answer"], event_id, when)
        second = self._answer(client, item, item["answer"], event_id, when)
        assert len(_attempts()) == before + 1
        assert first["correct"] == second["correct"]
        assert second["recorded"] is False

    def test_a_forged_token_is_still_refused(self, client):
        item = client.get("/api/pack?count=4").json()["items"][0]
        body, mac = item["token"].rsplit(".", 1)
        r = client.post("/api/practice/answer", json={
            "topic": item["topic"], "prompt": "", "answer": "", "given": "x",
            "token": body + "." + "0" * len(mac), "event_id": str(uuid.uuid7()),
            "at": "2026-09-18T20:18:00+00:00"})
        assert r.status_code == 400


class TestQueuedAnswersOutliveSecretRotation:
    """An answer queued offline is re-graded from its token when the learner
    reconnects, possibly weeks later. Rotating the origin guard, or moving item
    tokens onto their own secret, must not turn that answer into a 400."""

    ITEM = dict(topic="obj-case", prompt="Ma loen ___", answer="raamatut",
                distractor="raamat", lemma="raamat", hint="", rule="obj-case",
                why_ru="")

    def _issue(self):
        from types import SimpleNamespace

        from eesti import itemref

        return itemref.sign(SimpleNamespace(**self.ITEM),
                            {"kind": "practice", "v": itemref.GENERATOR_VERSION})

    @pytest.fixture(autouse=True)
    def _clean(self, monkeypatch):
        for name in ("ITEM_SECRET", "ITEM_SECRET_PREVIOUS", "PROXY_TOKEN", "STATE_TOKEN"):
            monkeypatch.delenv(name, raising=False)

    def test_a_dedicated_secret_still_accepts_tokens_issued_before_it(self, monkeypatch):
        from eesti import itemref

        monkeypatch.setenv("PROXY_TOKEN", "guard-1")
        queued = self._issue()
        monkeypatch.setenv("ITEM_SECRET", "items-1")
        assert itemref.verify(queued)["item"]["answer"] == "raamatut"

    def test_rotating_the_origin_guard_keeps_tokens_signed_by_the_item_secret(
            self, monkeypatch):
        from eesti import itemref

        monkeypatch.setenv("ITEM_SECRET", "items-1")
        monkeypatch.setenv("PROXY_TOKEN", "guard-1")
        queued = self._issue()
        monkeypatch.setenv("PROXY_TOKEN", "guard-2")
        assert itemref.verify(queued)["item"]["answer"] == "raamatut"

    def test_rotating_the_item_secret_keeps_the_previous_one_for_queued_answers(
            self, monkeypatch):
        from eesti import itemref

        monkeypatch.setenv("ITEM_SECRET", "items-1")
        queued = self._issue()
        monkeypatch.setenv("ITEM_SECRET", "items-2")
        monkeypatch.setenv("ITEM_SECRET_PREVIOUS", "items-1")
        assert itemref.verify(queued)["item"]["answer"] == "raamatut"
        monkeypatch.delenv("ITEM_SECRET_PREVIOUS")
        with pytest.raises(ValueError):
            itemref.verify(queued)

    def test_new_tokens_are_signed_with_the_item_secret_only(self, monkeypatch):
        from eesti import itemref

        monkeypatch.setenv("ITEM_SECRET", "items-2")
        monkeypatch.setenv("ITEM_SECRET_PREVIOUS", "items-1")
        monkeypatch.setenv("PROXY_TOKEN", "guard-1")
        issued = self._issue()
        monkeypatch.delenv("ITEM_SECRET_PREVIOUS")
        monkeypatch.delenv("PROXY_TOKEN")
        assert itemref.verify(issued)["item"]["answer"] == "raamatut"

    def test_a_token_from_some_other_key_is_refused(self, monkeypatch):
        from eesti import itemref

        monkeypatch.setenv("ITEM_SECRET", "someone-else")
        forged = self._issue()
        monkeypatch.setenv("ITEM_SECRET", "items-1")
        monkeypatch.setenv("PROXY_TOKEN", "guard-1")
        with pytest.raises(ValueError):
            itemref.verify(forged)
