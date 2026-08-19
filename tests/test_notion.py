"""Feeding the existing error log, without drowning it.

There is already a hand-kept `Vead` log in Notion, with a rule attached: three
or more rows sharing a tag become the focus of the week. That rule is what made
`obj-case` the documented priority in the first place.

Two things follow, and both are tested here rather than described.

**The tags are a closed set of nine.** They are `multi_select` options in a
database that already exists, and the counting rule is what gives them meaning.
An invented tag would not group, would never reach three, and would silently
never become anyone's focus — so it is refused at construction, not at push.

**Nothing is sent without a person looking.** A checker that appended every
suspicion would turn a curated record into a dump of model output and start the
rule firing on noise. Queueing is the default; pushing is a separate act.
"""

from __future__ import annotations

import pytest

from eesti.config import TAGS
from eesti.notion import Row, connect, mark_pushed, pending, queue, push


@pytest.fixture
def log(tmp_path):
    return connect(tmp_path / "notion.db")


def a_row(**kw):
    return Row(**{"wrong": "raamatut", "correct": "raamatu",
                  "why": "завершённое действие → omastav",
                  "tag": "obj-case", "on_date": "2026-08-19", **kw})


class TestTheClosedNine:
    def test_the_app_and_the_database_agree(self):
        """Read off the live database on 2026-08-19. If Notion's options ever
        drift from this list, rows stop grouping and the rule stops working."""
        assert TAGS == (
            "obj-case", "loc-case", "gen-stem", "gradation", "verb-form",
            "ma-da-inf", "word-order", "vocab", "rektsioon",
        )

    @pytest.mark.parametrize("tag", TAGS)
    def test_every_fixed_tag_is_accepted(self, tag):
        assert a_row(tag=tag).tag == tag

    def test_an_invented_tag_is_refused_at_construction(self):
        """Not at push time: a bad row must never reach the queue, or it sits
        there failing forever."""
        with pytest.raises(ValueError):
            a_row(tag="partitive-ish")


class TestQueueing:
    def test_a_correction_is_held_not_sent(self, log):
        assert queue(log, a_row()) is True
        assert [r["wrong"] for r in pending(log)] == ["raamatut"]

    def test_the_same_mistake_twice_is_one_row(self, log):
        """Otherwise a re-check of the same paragraph would push the count past
        three on its own, and invent a focus for the week."""
        queue(log, a_row())
        assert queue(log, a_row()) is False
        assert len(pending(log)) == 1

    def test_the_same_word_under_a_different_tag_is_a_different_row(self, log):
        queue(log, a_row())
        queue(log, a_row(tag="gen-stem"))
        assert len(pending(log)) == 2

    def test_a_pushed_row_leaves_the_queue(self, log):
        queue(log, a_row())
        mark_pushed(log, pending(log)[0]["id"])
        assert pending(log) == []


class TestPushing:
    def test_no_token_is_a_refusal_not_a_crash(self, monkeypatch):
        """A study session must never be interrupted by Notion being absent."""
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        ok, detail = push(a_row())
        assert ok is False
        assert "NOTION_TOKEN" in detail

    def test_a_failed_push_leaves_the_row_queued(self, log, monkeypatch):
        """The queue is the record until Notion confirms it has one."""
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        queue(log, a_row())
        ok, _ = push(a_row())
        assert ok is False
        assert len(pending(log)) == 1


class TestPayload:
    def test_the_property_names_match_the_database_exactly(self):
        """Notion matches properties by name; a typo silently drops the value."""
        assert set(a_row().properties()) == {
            "Vale (wrong)", "Õige (correct)", "Miks (why)", "Tag", "Kuupäev",
        }

    def test_the_wrong_fragment_is_the_title(self):
        title = a_row().properties()["Vale (wrong)"]["title"]
        assert title[0]["text"]["content"] == "raamatut"

    def test_the_tag_travels_as_a_multi_select_option(self):
        assert a_row().properties()["Tag"]["multi_select"] == [{"name": "obj-case"}]

    def test_the_explanation_is_russian_and_survives_the_trip(self):
        """A Russian-speaking learner reading an Estonian-only explanation is
        the failure this whole choice exists to avoid."""
        why = a_row().properties()["Miks (why)"]["rich_text"][0]["text"]["content"]
        assert "завершённое" in why


class TestTheQueueCanActuallyBeDrained:
    """Corrections could be queued from the app and pushed only by
    `cli notion --push`. The CLI does not exist on the deployment — the
    container is ephemeral and the learner is on a phone — so the queue filled
    and never drained, and the readiness verdict counted queued rows as
    writing evidence, measuring the queue rather than the log it feeds."""

    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        monkeypatch.setattr(app_module, "NOTION_DB", str(tmp_path / "n.db"))
        return TestClient(app_module.app)

    def queue_one(self, client, wrong="raamatut"):
        client.post("/api/notion/queue", json={
            "wrong": wrong, "correct": "raamatu",
            "why": "täissihitis", "tag": "obj-case"})
        return client.get("/api/notion/pending").json()["items"][-1]["id"]

    def test_there_is_a_push_route_at_all(self, client, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "t")
        row_id = self.queue_one(client)
        assert client.post("/api/notion/push",
                           json={"ids": [row_id]}).status_code != 405

    def test_without_a_token_it_says_so_and_keeps_the_rows(self, client,
                                                           monkeypatch):
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        row_id = self.queue_one(client)
        got = client.post("/api/notion/push", json={"ids": [row_id]})
        assert got.status_code == 503
        assert "NOTION_TOKEN" in got.json()["detail"]
        assert client.get("/api/notion/pending").json()["items"]

    def test_the_page_is_told_before_the_button_is_pressed(self, client,
                                                           monkeypatch):
        """A button that looks live and 503s is worse than one that says why."""
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        assert client.get("/api/notion/pending").json()["can_push"] is False
        monkeypatch.setenv("NOTION_TOKEN", "t")
        assert client.get("/api/notion/pending").json()["can_push"] is True

    def test_it_takes_named_rows_not_the_whole_queue(self, client, monkeypatch):
        """The Vead log is worth having only while it stays curated: three rows
        sharing a tag become the focus of the week, and that rule is what
        identified obj-case. An endpoint that drained the queue wholesale would
        be the same mistake as appending every suspicion, one step later.

        Tested by asking for a bulk push and being refused, rather than by
        inspecting the signature — `from __future__ import annotations` makes
        the annotation a string, and a test that reads it is testing the import
        style."""
        from eesti import notion

        monkeypatch.setenv("NOTION_TOKEN", "t")
        sent = []
        monkeypatch.setattr(notion, "push",
                            lambda row, token=None: (sent.append(row), (True, "ok"))[1])
        self.queue_one(client, "raamatut")
        self.queue_one(client, "autot")
        for body in ({}, {"ids": []}, {"all": True}):
            assert client.post("/api/notion/push", json=body).status_code == 422
        assert sent == [], "a request that named no rows sent something"
        assert len(client.get("/api/notion/pending").json()["items"]) == 2

    def test_a_failed_row_stays_queued(self, client, monkeypatch):
        """The queue is the record until Notion confirms it has one."""
        from eesti import notion

        monkeypatch.setenv("NOTION_TOKEN", "t")
        monkeypatch.setattr(notion, "push", lambda row, token=None: (False, "boom"))
        row_id = self.queue_one(client)
        got = client.post("/api/notion/push", json={"ids": [row_id]}).json()
        assert got["sent"] == []
        assert got["failed"][0]["detail"] == "boom"
        assert got["remaining"] == 1

    def test_a_sent_row_leaves_the_queue(self, client, monkeypatch):
        from eesti import notion

        monkeypatch.setenv("NOTION_TOKEN", "t")
        monkeypatch.setattr(notion, "push", lambda row, token=None: (True, "ok"))
        row_id = self.queue_one(client)
        got = client.post("/api/notion/push", json={"ids": [row_id]}).json()
        assert got["sent"] == [row_id] and got["remaining"] == 0

    def test_an_unknown_id_does_not_fail_the_others(self, client, monkeypatch):
        from eesti import notion

        monkeypatch.setenv("NOTION_TOKEN", "t")
        monkeypatch.setattr(notion, "push", lambda row, token=None: (True, "ok"))
        row_id = self.queue_one(client)
        got = client.post("/api/notion/push",
                          json={"ids": [row_id, 9999]}).json()
        assert got["sent"] == [row_id]
        assert got["failed"] == [{"id": 9999, "detail": "not queued"}]
