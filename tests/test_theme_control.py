"""The Sõnavara teema control, and whether it does anything.

A theme picks **words**; the path picks the **rule**. Two axes, and the page
offered the word axis on every topic — including the seven drillable ones where
there is no word to vary. Choosing *Kodu ja elamine* on `küsisõnad` produced
exactly the same ten drills: no error, no note, no difference. That is
indistinguishable from the app ignoring the click, and it is what a learner
reported after trying it.

It is also this project's most-repeated defect in a new costume. The list so
far: a measurement nothing wrote to, an endpoint nothing called, a
`[data-theme]` nothing set, a `kind="vocab"` nothing inserted, a `FAMILIAR`
rung nothing wrote — and now a filter nothing applies.

So the answer lives in exactly one function, `practice.theme_slot`, which the
generator dispatch reads to build its `only` set and the API reads to tell the
page whether to offer the control at all. These check that the three stay one
thing.
"""

from __future__ import annotations

import re

import pytest

from fastapi.testclient import TestClient

from eesti.app import app
from eesti.curriculum import TOPICS, by_id
from eesti.practice import THEME_SLOTS, theme_slot


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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
    """`items_for` computes one `only` set from `theme_slot` and hands it to
    whichever generator owns the topic. It used to compute three sets up front
    and pick between them at each branch, which is two places to keep in step —
    and they were not in step: `vordlusastmed` and `jargarvud` were handed
    `only=None` while the page offered them a theme."""

    def test_items_for_reads_theme_slot_and_nothing_else(self):
        import inspect

        from eesti import practice

        source = inspect.getsource(practice.items_for)
        assert "theme_slot(topic)" in source
        # One `only`, computed once. Three named sets is the shape that drifted.
        for gone in ("nouns =", "verbs =", "countable ="):
            assert gone not in source, f"{gone} is back — two places again"

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
        """`küsisõnad` is a closed class of question words. It was the topic on
        screen when the control was reported as doing nothing."""
        rows = {r["id"]: r for r in client.get("/api/curriculum").json()["topics"]}
        assert rows["kusisonad"]["themed"] is False
        # ...and one that genuinely varies its nouns still offers it.
        assert rows["pohivormid"]["themed"] is True


class TestThePageActsOnIt:
    def test_the_select_is_disabled_rather_than_left_lying(self, page):
        assert "themeApplies" in page
        assert re.search(r"sel\.disabled = true", page)

    def test_a_theme_is_not_sent_when_it_would_be_ignored(self, page):
        """Disabling the control is not enough on its own: a value left in it
        from a previous topic would still be posted."""
        assert 'const theme = themeApplies() ? $("#wordTheme").value : "";' in page

    def test_the_two_axes_are_named_on_screen(self, page):
        """The learner's actual question was "is this list connected to that
        select?". The answer is no, and nothing said so."""
        assert 'id="themeNote"' in page
        assert "Kogu rada" in page
