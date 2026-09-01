"""Every destination has a mark, and every mark has a destination.

`NAV_ICON` and `MODE_ICON` are hand-written maps keyed on the tab and mode
names — exactly the kind of second list this repo keeps getting caught by. The
`TABS` list drifted from the panels it described and three of ten panels never
showed; `RU` drifted from `progress.TopicProgress.state` and a finished topic
rendered the English word `mastered`. Both failed silently, because every row
still rendered *something*.

An icon map fails the same way and even more quietly: a tab with no entry keeps
its label and simply has no picture, which looks like a design choice rather
than a gap. So this asks the page which destinations exist and checks the maps
against that, in both directions.

The spacing checks below are here for the same reason. Eleven different
vertical margins had been chosen one element at a time, and the `margin-top:0`
idiom — "I am first in this panel, the padding already spaces me" — had been
copied onto four elements that are *not* first, where it silently deleted the
space they needed. One of the four was the crowding on the path screen that
started this work.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pagesrc import markup, markup_and_script, styles



@pytest.fixture(scope="module")
def page() -> str:
    return markup_and_script()


@pytest.fixture(scope="module")
def css(page) -> str:
    # The stylesheet is `eesti/web/app.css` now, not a `<style>` block in the
    # page. Same text, one fewer slice.
    return styles()


def map_keys(page: str, name: str) -> set[str]:
    block = page[page.index(name):]
    return set(re.findall(r"^\s*([a-z]+):\s*'", block[:block.index("\n};")], re.M))


def _markup(_page: str) -> str:
    """The authored HTML only.

    Scanning the whole app picks up `data-tab="${tab}"` out of the selector
    strings in the modules, which is not a destination — it is the code that
    goes looking for one. So this reads `index.html` and nothing else, and
    still strips the one inline script in it.

    Strips the script blocks rather than truncating at the first one: the
    theme is applied by a small inline script immediately after `<body>`, so
    cutting at `index("<script>")` leaves the head and nothing else, and every
    check below passes on an empty set.
    """
    return re.sub(r"<script>.*?</script>", "", markup(), flags=re.S)


def markup_tabs(page: str) -> set[str]:
    return set(re.findall(r'button[^>]*\bdata-tab="([^"]+)"', _markup(page)))


def markup_modes(page: str) -> set[str]:
    return set(re.findall(r'button[^>]*\bdata-mode="([^"]+)"', _markup(page)))


class TestTheMapsMatchThePage:
    def test_there_are_destinations_to_check(self, page):
        """Guard against a regex that matches nothing and makes the rest of
        this file vacuous — the failure mode two tests in this suite have
        already had."""
        assert len(markup_tabs(page)) >= 10
        assert len(markup_modes(page)) == 3

    def test_every_tab_has_an_icon(self, page):
        missing = sorted(markup_tabs(page) - map_keys(page, "const NAV_ICON = {"))
        assert not missing, (
            f"these tabs render a label with no mark beside it: {missing}")

    def test_no_icon_is_drawn_for_a_tab_that_does_not_exist(self, page):
        extra = sorted(map_keys(page, "const NAV_ICON = {") - markup_tabs(page))
        assert not extra, f"icon for a destination the page does not have: {extra}"

    def test_every_mode_has_an_icon(self, page):
        missing = sorted(markup_modes(page) - map_keys(page, "const MODE_ICON = {"))
        assert not missing, f"modes with no mark: {missing}"

    def test_the_marks_are_painted_from_the_maps(self, page):
        """Written into the DOM rather than into eighteen buttons, so a
        destination added later gets its mark by being in the map."""
        assert "function paintIcons()" in page
        assert "paintIcons();" in page, "the painter is never called"

    def test_skills_and_modes_are_told_apart_by_form(self, css):
        """Not by a second accent colour: the app has one accent on purpose,
        and a segmented control next to a row of outlined pills is already two
        recognisably different kinds of control."""
        assert 'nav[data-mode-nav] button:not([aria-selected="true"]){border-color' in css
        assert ".modes button[aria-selected=" in css


class TestSpacingComesFromTheScale:
    def test_the_scale_exists(self, css):
        for step in ("--s1", "--s2", "--s3", "--s4", "--s5"):
            assert f"{step}:" in css, f"{step} is not defined"

    def test_no_element_carries_a_raw_pixel_margin_inline(self, page):
        """Twenty-eight inline declarations used ten different values. An
        inline margin is unreachable from the stylesheet, so the only way to
        change spacing was to find every one of them."""
        # Only the margin declaration itself. A `font-size:17px` sitting after
        # it in the same attribute is type, not layout, and is not this rule's
        # business -- the first version of this regex flagged two of those.
        raw = [m.group(0) for m in
               re.finditer(r'margin[a-z-]*:\s*[^;"]*\d+px[^;"]*', page)
               if 'style="' in page[max(0, m.start() - 120):m.start()]]
        assert not raw, f"inline pixel margins left: {raw}"

    def test_first_child_spacing_is_a_rule_not_an_attribute(self, page, css):
        """Thirteen elements said "I am first in this panel" by hand. Four of
        them were not first, and there the reset deleted real space."""
        assert ".panel > :first-child{margin-top:0}" in css
        assert 'style="margin-top:0"' not in page, (
            "an inline reset is back; it cannot distinguish a first child from "
            "one that merely looked like it needed the same line")
