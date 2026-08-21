"""The path's five states, checked against the code that produces them.

`progress.TopicProgress.state` is the only thing that decides what state a
topic is in. The page has to gloss each one in Russian and mark each one with
an icon, and both of those lists were written by hand from what happened to be
on screen at the time.

That is how `mastered` stayed English. A previous pass found three state
badges rendering as `REFERENCE`, `READY` and `LOCKED` and glossed exactly
those three -- because those three are what an account with no progress shows.
`mastered` and `in progress` only appear *after* the learner has answered
something, so nobody saw them, and `RU` acquired `done` and `review` instead,
which the code has never emitted. A learner who finished a topic was shown the
English word `mastered` as their reward.

The lesson is the one this repo keeps relearning: a list of things that already
exist somewhere else drifts from the thing it describes, and it drifts silently,
because every row still renders *something*. So this asks the source.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "eesti" / "web" / "index.html"


def emitted_states() -> set[str]:
    """Every string `TopicProgress.state` can return, read off the property."""
    from eesti.progress import TopicProgress

    source = inspect.getsource(TopicProgress.state.fget)
    # Covers the ternary too: the naive `return "..."` pattern misses
    # `return "in progress" if self.attempts else "ready"`, which is exactly
    # one of the two states that went missing.
    return set(re.findall(r'"([a-z ]+)"', source))


def _object_keys(page: str, name: str) -> set[str]:
    block = page[page.index(name):]
    return set(re.findall(r'"([a-z ]+)"\s*:', block[:block.index("\n};")]))


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def states() -> set[str]:
    return emitted_states()


class TestTheSourceOfTruthIsProgressPy:
    def test_there_are_states_to_check(self, states):
        """A regex that matched nothing would make every test below vacuous."""
        assert len(states) >= 4
        assert "mastered" in states and "in progress" in states


class TestEveryStateIsReadable:
    def test_each_one_has_a_russian_gloss(self, page, states):
        glossed = _object_keys(page, "const RU = {")
        missing = sorted(states - glossed)
        assert not missing, (
            "these reach the screen as the raw English key, which is a "
            f"database value shown to a learner: {missing}")

    def test_the_gloss_is_actually_russian(self, page, states):
        block = page[page.index("const RU = {"):]
        block = block[:block.index("\n};")]
        for state in sorted(states):
            m = re.search(rf'"{re.escape(state)}"\s*:\s*"([^"]+)"', block)
            assert m, f"no gloss for {state!r}"
            assert any("Ѐ" <= ch <= "ӿ" for ch in m.group(1)), (
                f"{state} renders as {m.group(1)!r}")

    def test_no_gloss_describes_a_state_that_cannot_happen(self, page, states):
        """The other direction. `done` and `review` sat in the map for states
        nothing emits -- harmless on their own, and the reason the two real
        ones looked covered."""
        glossed = _object_keys(page, "const RU = {")
        # `RU` also carries tab and rail labels; only judge the ones that look
        # like path states, which are the lower-case multi-word keys.
        statelike = {k for k in glossed if k.islower() and not k[0].isupper()}
        invented = sorted(statelike - states)
        assert not invented, (
            f"glossed but never emitted: {invented}")


class TestEveryStateIsMarked:
    """Colour alone does not distinguish a state for every learner, so each
    one carries a shape as well."""

    def test_each_one_has_an_icon(self, page, states):
        icons = _object_keys(page, "const STATE_ICON = {")
        missing = sorted(states - icons)
        assert not missing, f"no icon for: {missing}"

    def test_no_icon_is_drawn_for_a_state_that_cannot_happen(self, page, states):
        icons = _object_keys(page, "const STATE_ICON = {")
        assert not sorted(icons - states), f"icon for nothing: {sorted(icons - states)}"

    def test_each_state_gets_its_own_colour(self, page, states):
        """`locked` is the exception: it is dimmed as a whole row rather than
        recoloured, because it is the one state that is not a thing to do."""
        css = page[page.index("<style>"):page.index("</style>")]
        for state in sorted(states):
            cls = state.replace(" ", "-")
            assert f".topic.{cls}" in css, (
                f"{state} renders in the default grey like every other state")
