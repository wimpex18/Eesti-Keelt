"""CSS rules a browser found and markup tests cannot see.

`[hidden]{display:none!important}` must come first: an author rule such as
`nav{display:flex}` otherwise beats the browser's own `[hidden]`, leaving hidden
navigation laid out on top of the visible one.
"""

from __future__ import annotations

import re

import pytest

from pagesrc import everything



@pytest.fixture(scope="module")
def css() -> str:
    """The stylesheet and the markup in one string (stylesheet last), so ordering
    assertions compare positions inside the CSS.
    """
    return everything()


def test_hidden_beats_the_display_rules(css):
    """Without `!important` the attribute is decoration."""
    assert re.search(r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important", css)


def test_it_comes_before_the_nav_rule_it_has_to_beat(css):
    """Keeping `[hidden]` first covers rules added later."""
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


def test_the_source_footer_clears_the_fixed_navigation(css):
    """The page's bottom padding clears the phone's fixed mode bar, so the attribution
    footer is not covered.
    """
    rule = re.search(r"footer\.sources\{[^}]*\}", css, re.S)
    assert rule, "the footer must have its own rule"
    body = rule.group(0)
    padding = re.search(r"padding:[^;}]*", body).group(0)
    # Three values or a padding-bottom: the last one has to clear a ~48px bar
    # plus its safe area, and `0 var(--s3)` does not.
    assert re.search(r"padding:[^;}]*\s\d{2,}px", padding), (
        f"no bottom padding to clear the fixed nav: {padding}")
