"""The Teema control, and whether it does anything.

A theme picks words; the path picks the rule. Closed-class topics have no word
to vary, so the control must not be offered there. `practice.theme_slot` is the
single answer, read by the generator dispatch and by the API that tells the page
whether to offer the control.
"""

from __future__ import annotations

import re

import pytest

from eesti.curriculum import TOPICS, by_id
from eesti.practice import THEME_SLOTS, theme_slot


@pytest.fixture(scope="module")
def drillable():
    topics = [t for t in TOPICS if t.generator is not None]
    assert len(topics) > 20, "no drillable topics — every check below is vacuous"
    return topics


class TestTheAnswerIsWellFormed:
    def test_every_slot_is_one_the_generator_can_use(self, drillable):
        for topic in drillable:
            slot = theme_slot(topic.id)
            assert slot is None or slot in THEME_SLOTS, (topic.id, slot)

    def test_some_topics_can_and_some_cannot(self, drillable):
        """If everything answered the same way the control would be pointless
        in one direction or dishonest in the other."""
        answers = {theme_slot(t.id) is not None for t in drillable}
        assert answers == {True, False}

    def test_a_topic_with_no_generator_has_no_slot(self):
        """A reference topic has no drills, so it cannot have themed ones."""
        for topic in TOPICS:
            if topic.generator is None:
                assert theme_slot(topic.id) is None


class TestTheClaimMatchesTheGenerator:
    """`items_for` passes one `only` set, from `theme_slot`, to every generator branch."""

    def test_every_branch_passes_the_same_only(self):
        import inspect

        from eesti import practice

        source = inspect.getsource(practice.items_for)
        passed = set(re.findall(r"only=(\w+)", source))
        assert passed == {"only"}, f"branches disagree: {sorted(passed)}"


class TestTheApiTellsThePageTheTruth:
    def test_curriculum_carries_themed_for_every_topic(self, client):
        rows = client.get("/api/curriculum").json()["topics"]
        assert rows
        for row in rows:
            assert "themed" in row, row["id"]

    def test_themed_is_exactly_what_the_generator_will_do(self, client):
        """The whole point: the page must not promise a filter the drill will
        not apply, nor withhold one it would."""
        for row in client.get("/api/curriculum").json()["topics"]:
            expected = (by_id(row["id"]).generator is not None
                        and theme_slot(row["id"]) is not None)
            assert row["themed"] is expected, row["id"]

    def test_the_topic_that_prompted_this_is_marked_unthemed(self, client):
        """`küsisõnad` (a closed class) has no theme slot."""
        rows = {r["id"]: r for r in client.get("/api/curriculum").json()["topics"]}
        assert rows["kusisonad"]["themed"] is False
        # ...and one that genuinely varies its nouns still offers it.
        assert rows["pohivormid"]["themed"] is True


class TestThePageActsOnIt:
    def test_the_select_is_disabled_rather_than_left_lying(self, page):
        assert "themeApplies" in page
        assert re.search(r"sel\.disabled = true", page)

    def test_a_theme_is_not_sent_when_it_would_be_ignored(self, page):
        """A disabled control posts no leftover theme value."""
        assert 'const theme = themeApplies() ? $("#wordTheme").value : "";' in page

    def test_the_two_axes_are_named_on_screen(self, page):
        """The page explains that the word list and the theme select are separate."""
        assert 'id="themeNote"' in page
        assert "Kogu rada" in page


class TestTheDeadEnd:
    """A theme × topic pair that yields nothing tells the learner and offers a
    one-click retry without the theme (corpus topics often lack a sentence with a
    theme noun).
    """

    def test_the_grid_still_has_dead_ends(self):
        """If this ever stops being true the message below is dead code, and a
        message nobody can reach is the thing this file exists to catch."""
        from eesti.practice import items_for

        empty = 0
        for topic, theme in (("mitmus", "kodu"), ("mitmus", "ilm"),
                             ("kohakaanded", "riided")):
            if not items_for(topic, count=10, seed=1, theme=theme):
                empty += 1
        assert empty, "no dead end left — the retry path is unreachable"

    def test_an_emptied_theme_is_not_reported_as_a_broken_generator(self, client):
        body = client.post("/api/practice",
                           json={"topic": "mitmus", "theme": "kodu", "count": 10}).json()
        if body["items"]:
            pytest.skip("this pair is no longer empty on the fixture corpus")
        assert body["theme_emptied"] is True
        assert "генератор" not in (body["detail"] or "").lower()

    def test_a_theme_that_worked_is_not_flagged(self, client):
        body = client.post("/api/practice",
                           json={"topic": "pohivormid", "count": 10}).json()
        assert body["theme_emptied"] is False

    def test_the_response_says_which_theme_was_applied(self, client):
        """The page guards the control, but the contract must answer for
        itself: a caller sending a theme to a closed-class topic had no way to
        learn it had been dropped."""
        dropped = client.post(
            "/api/practice",
            json={"topic": "kusisonad", "theme": "kodu", "count": 5}).json()
        assert dropped["theme"] is None, "a dropped theme is reported as applied"

    def test_the_page_offers_the_way_out(self, page):
        assert "res.theme_emptied" in page
        assert "Proovi ilma teemata" in page
        assert '$("#wordTheme").value = ""' in page
