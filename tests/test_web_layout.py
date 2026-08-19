"""One rule in the page's CSS, pinned because a browser found it and no other
test could have.

The page has two bottom navigation bars — one for learning, one for exam prep —
and the JavaScript hides the inactive one by setting the `hidden` attribute.
That is correct, and it did nothing: `nav{display:flex}` is an *author* rule,
and an author rule beats the browser's own `[hidden]{display:none}`. So the
hidden bar stayed laid out, and on a 390px phone two fixed bars sat on top of
each other, both painting, at the same 48 pixels of screen.

Driving the page in a real browser showed it as geometry: `Ülevaade` occupying
x 4–131 while `Rada` and `Lugemine` occupied x 4–67 and 67–130, all at the
bottom edge. A test that renders markup without layout cannot see that, and
neither can a person reading the CSS, because the bug is in what the rule
*overrides* rather than in the rule itself.

Rather than put a browser in CI for one line, this asserts the line is there.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parent.parent / "eesti" / "web" / "index.html"


@pytest.fixture(scope="module")
def css() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_hidden_beats_the_display_rules(css):
    """Without `!important` the attribute is decoration."""
    assert re.search(r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important", css)


def test_it_comes_before_the_nav_rule_it_has_to_beat(css):
    """Specificity ties are broken by order, and `[hidden]` versus `nav` is not
    a tie — but keeping it first means it also covers whatever is added later."""
    assert css.index("[hidden]") < css.index("nav{display:flex")


def test_both_navigations_still_exist(css):
    """If one is ever removed, the rule above stops mattering and this test
    should be revisited rather than silently passing forever."""
    assert 'data-mode-nav="learn"' in css
    assert 'data-mode-nav="exam"' in css


def test_the_inactive_one_ships_hidden(css):
    """The exam navigation must start hidden; the learner lands on learning."""
    exam = re.search(r'<nav[^>]*data-mode-nav="exam"[^>]*>', css)
    assert exam and "hidden" in exam.group(0)
