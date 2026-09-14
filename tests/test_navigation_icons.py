"""Every destination has a mark, and every mark has a destination.

`NAV_ICON` and `MODE_ICON` are hand-written maps, so they are checked against
the tabs and modes the page actually has, in both directions. Spacing checks:
margins use the scale tokens, and only the real first child of a panel has its
top margin reset.
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
    # The stylesheet is `eesti/web/app.css`.
    return styles()


def map_keys(page: str, name: str) -> set[str]:
    block = page[page.index(name):]
    return set(re.findall(r"^\s*([a-z]+):\s*'", block[:block.index("\n};")], re.M))


def _markup(_page: str) -> str:
    """The authored HTML only (`index.html` with script blocks stripped), so selector
    strings in modules are not mistaken for destinations.
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
        """No inline margins: spacing lives in the stylesheet."""
        # Only the margin declaration itself. A `font-size:17px` sitting after
        # it in the same attribute is type, not layout, and is not this rule's
        # business -- the first version of this regex flagged two of those.
        raw = [m.group(0) for m in
               re.finditer(r'margin[a-z-]*:\s*[^;"]*\d+px[^;"]*', page)
               if 'style="' in page[max(0, m.start() - 120):m.start()]]
        assert not raw, f"inline pixel margins left: {raw}"

    def test_first_child_spacing_is_a_rule_not_an_attribute(self, page, css):
        """Only a panel's real first child has its top margin reset (`.panel >
        :first-child`).
        """
        assert ".panel > :first-child{margin-top:0}" in css
        assert 'style="margin-top:0"' not in page, (
            "an inline reset is back; it cannot distinguish a first child from "
            "one that merely looked like it needed the same line")


def _chrome() -> str:
    return (Path(__file__).resolve().parents[1]
            / "eesti" / "web" / "js" / "chrome.js").read_text(encoding="utf-8")


def _block(name: str) -> str:
    src = _chrome()
    block = src[src.index(f"const {name} = {{"):]
    return block[:block.index("\n};")]


def _drawn() -> set[str]:
    return set(re.findall(r"^\s{2}([a-z]+):", _block("UI_ICON"), re.M))


def _button_map() -> dict[str, str]:
    return dict(re.findall(r'(\w+):\s*"([a-z]+)"', _block("BUTTON_ICON")))


def _asked() -> set[str]:
    """Every mark the app asks for, via `uiIcon("x")` or `emptyState({icon: "x"})`."""
    src = markup_and_script()
    return (set(re.findall(r'uiIcon\(\s*"([a-z]+)"', src))
            | set(re.findall(r'icon:\s*"([a-z]+)"', src))
            | set(_button_map().values()))


class TestTheInterfaceMarks:
    """`UI_ICON` and `BUTTON_ICON` agree with the page and modules in both directions:
    no id without an element, no requested name without a mark.
    """

    def test_every_button_it_decorates_is_in_the_page(self):
        page = markup()
        missing = [i for i in _button_map() if f'id="{i}"' not in page]
        assert not missing, (
            f"BUTTON_ICON names ids the page does not have: {missing}. "
            "The mark is painted by id, so these paint nothing.")

    def test_every_mark_the_app_asks_for_is_drawn(self):
        unknown = sorted(_asked() - _drawn())
        assert not unknown, (
            f"marks asked for but not drawn: {unknown}. `uiIcon` returns an "
            "empty string for a name it does not have, so this is invisible.")

    def test_no_mark_is_drawn_and_never_used(self):
        unused = sorted(_drawn() - _asked())
        assert not unused, (
            f"marks drawn but never asked for: {unused}. Delete them or use them.")
