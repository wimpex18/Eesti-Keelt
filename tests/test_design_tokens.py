"""The stylesheet asked about itself.

A declaration that cannot work fails silently: `var(--ok)` with no `--ok`
defined renders as inheritance, invisible in review and screenshots. So every
token read is a token defined, painting tokens exist in both palettes, and
related values stay derived.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pagesrc import markup_and_script, styles


#: Properties the browser defines for us. `--pct` is declared with `@property`
#: and set from JavaScript; it has an `initial-value`, so it always resolves.
DECLARED_ELSEWHERE = {"--pct"}


@pytest.fixture(scope="module")
def css() -> str:
    return styles()


def defined_tokens(css: str) -> set[str]:
    """Every custom property the sheet gives a value to."""
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", css)) | DECLARED_ELSEWHERE


def used_tokens(css: str) -> set[str]:
    """Every custom property the sheet reads, ignoring those with a fallback."""
    return {m.group(1) for m in re.finditer(r"var\(\s*(--[a-z0-9-]+)\s*\)", css)}


class TestEveryTokenReadIsATokenWritten:
    def test_no_declaration_reads_an_undefined_custom_property(self, css):
        missing = sorted(used_tokens(css) - defined_tokens(css))
        assert not missing, (
            "these resolve to nothing, so the declaration using them does "
            f"nothing and says so nowhere: {missing}")

    def test_there_are_tokens_to_check(self, css):
        """The guard against a regex that quietly matches nothing -- the exact
        failure this file exists to catch, one level up."""
        assert len(used_tokens(css)) >= 15
        assert len(defined_tokens(css)) >= 15


class TestBothThemesDefineTheSameTokens:
    """Every painting token is defined in the dark palette too, or it falls back to
    `inherit` and may land on its own background.
    """

    #: A token paints when its value is a colour; lengths, durations and easings are
    #: theme-neutral. Classified by value, not by a name list.
    COLOURISH = re.compile(r"#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(|color-mix\(")

    def _block(self, css: str, opener: str) -> dict[str, str]:
        start = css.index(opener)
        body = css[start:css.index("}", start)]
        return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;}]+)", body))

    def test_the_dark_palettes_cover_what_light_defines(self, css):
        light = self._block(css, ":root{\n")
        # Both dark declarations: the media query for "system dark", and the
        # explicit stamp that has to beat a light OS.
        stamped = self._block(css, ':root[data-theme="dark"]{')
        queried = self._block(css, ':root:not([data-theme="light"]){')

        paints = {n for n, v in light.items() if self.COLOURISH.search(v)}
        assert paints, "no colour tokens found -- the check would be vacuous"

        for name, block in (("data-theme=dark", stamped),
                            ("prefers-color-scheme:dark", queried)):
            missing = sorted(paints - set(block))
            assert not missing, (
                f"{name} leaves these at their light values: {missing}")

    def test_the_two_dark_palettes_agree(self, css):
        """They are written twice, so they can drift. An explicit dark choice
        and a dark OS must produce the same page."""
        stamped = set(self._block(css, ':root[data-theme="dark"]{'))
        queried = set(self._block(css, ':root:not([data-theme="light"]){'))
        assert stamped == queried, (
            "the two dark palettes define different tokens: "
            f"only stamped={sorted(stamped - queried)}, "
            f"only queried={sorted(queried - stamped)}")


class TestMotionIsOptional:
    """Everything added for feel has to be removable by the person who asked
    the operating system to remove it."""

    def test_every_transition_target_is_named_in_the_reduced_motion_block(self, css):
        block = css[css.index("@media (prefers-reduced-motion:reduce)"):]
        block = block[:block.index("\n  }")]
        assert "transition:none" in block
        for selector in (".lib-item", ".vocword", ".topic", "nav button",
                         ".modes button", ".ring"):
            assert selector in block, (
                f"{selector} animates but is not switched off for "
                "prefers-reduced-motion")


class TestTheRingCanActuallyAnimate:
    """`--pct` is registered with `@property` (`syntax:"<number>"`), without which its
    transition does not animate.
    """

    def test_the_property_is_registered(self, css):
        assert "@property --pct" in css, (
            "without this the transition below is a no-op that looks correct")
        block = css[css.index("@property --pct"):]
        assert 'syntax:"<number>"' in block[:block.index("}")], (
            "an untyped registration does not interpolate either")

    def test_and_something_transitions_it(self, css):
        assert re.search(r"\.ring\{transition:--pct", css), (
            "the property is registered but nothing animates it")


@pytest.fixture(scope="module")
def page() -> str:
    """The page and its modules. The theme mechanism spans both: the stylesheet
    branches on `[data-theme]`, the inline head script restores it before the
    first paint, and `chrome.js` cycles it."""
    return markup_and_script()


class TestTheThemeAttributeHasAWriter:
    """`[data-theme]` has a control that sets it."""

    def test_something_sets_what_the_stylesheet_reads(self, page):
        css = styles()
        assert "[data-theme=" in css, "the stylesheet no longer reads it"
        assert ("dataset.theme" in page
                or 'setAttribute("data-theme"' in page), (
            "the stylesheet branches on an attribute nothing writes")

    def test_system_stays_reachable(self, page):
        """Two states would be a trap: the browser's default is the *absence*
        of the attribute, so a light/dark toggle that can only stamp a value
        locks the page out of following the OS ever again."""
        block = page[page.index("const THEMES = ["):]
        block = block[:block.index("\n];")]
        for state in ("system", "light", "dark"):
            assert f'"{state}"' in block, f"no {state} state in the cycle"
        assert "delete document.documentElement.dataset.theme" in page, (
            "nothing removes the attribute, so `system` cannot be returned to")

    def test_the_choice_is_applied_before_the_first_paint(self, page):
        """Restoring it from the module at the end of the file means the
        browser paints the light page first and then repaints -- a white flash
        on every load for whoever chose dark."""
        head = page[:page.index("<div class=\"wrap\">")]
        assert 'localStorage.getItem("theme")' in head, (
            "the stored theme is read too late to prevent a flash")

    def test_storage_access_cannot_break_the_page(self, page):
        """`localStorage` throws outright in some contexts rather than
        returning null, and this runs before anything else on the page."""
        block = page[page.index('localStorage.getItem("theme")') - 300:]
        assert "try" in block[:400] and "catch" in block[:600]


class TestTheChromeOutsideThePageAgreesWithIt:
    """The theme-colour meta tag, the manifest's colours and the offline page use the
    stylesheet's `--bg`, read from the stylesheet.
    """

    @pytest.fixture
    def bg(self, css):
        found = re.search(r"--bg:\s*(#[0-9a-fA-F]{6})", css)
        assert found, "no --bg in the stylesheet"
        return found.group(1).lower()

    def test_the_status_bar_matches_the_page(self, bg):
        page = (Path(__file__).resolve().parents[1]
                / "eesti" / "web" / "index.html").read_text(encoding="utf-8")
        found = re.search(
            r'theme-color"\s+media="\(prefers-color-scheme: light\)"\s+content="(#[0-9a-fA-F]{6})"',
            page)
        assert found and found.group(1).lower() == bg, (
            f"theme-color is {found and found.group(1)!r}, --bg is {bg!r}")

    def test_the_installed_splash_matches_the_page(self, bg):
        manifest = (Path(__file__).resolve().parents[1]
                    / "eesti" / "api" / "assets.py").read_text(encoding="utf-8")
        found = re.search(r'"background_color":\s*"(#[0-9a-fA-F]{6})"', manifest)
        assert found and found.group(1).lower() == bg, (
            f"manifest background_color is {found and found.group(1)!r}, --bg is {bg!r}")

    def test_the_offline_page_matches_the_page(self, bg):
        worker = (Path(__file__).resolve().parents[1]
                  / "eesti" / "web" / "sw.js").read_text(encoding="utf-8")
        assert f"background:{bg}" in worker, (
            f"the offline page does not paint {bg}")
