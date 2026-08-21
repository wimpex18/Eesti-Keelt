"""The two ways a stylesheet lies quietly.

A CSS declaration that cannot work does not fail, does not warn and does not
show up in any screenshot as anything other than "the default". Both kinds
found on 2026-08-21 had been in the file for as long as anyone had looked at
it:

  * ``.vocword{color:var(--fg)}`` -- there is no ``--fg``; the token is
    ``--ink``. The chip took its colour from inheritance, which happened to be
    the same, so the line was decorative in the literal sense.
  * ``.topic.mastered .st{color:var(--ok)}`` -- there is no ``--ok`` either.
    This one *did* match a real element: ``mastered`` is a state
    ``progress.TopicProgress.state`` emits. So the one row in the whole path
    list that represents finished work was styled by a rule that resolved to
    nothing.

Neither is catchable by review -- ``var(--ok)`` reads as correct until you go
looking for the definition -- and neither is catchable by a layout assertion,
because the element is present, sized and visible. What catches them is asking
the sheet about itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "eesti" / "web" / "index.html"

#: Properties the browser defines for us. `--pct` is declared with `@property`
#: and set from JavaScript; it has an `initial-value`, so it always resolves.
DECLARED_ELSEWHERE = {"--pct"}


@pytest.fixture(scope="module")
def css() -> str:
    page = PAGE.read_text(encoding="utf-8")
    return page[page.index("<style>"):page.index("</style>")]


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
    """A token defined only in the light palette renders as *nothing* in dark,
    which is the unreadable-artifact bug: text painted with an unresolved
    colour falls back to `inherit` and can land on its own background."""

    def _block(self, css: str, opener: str) -> set[str]:
        start = css.index(opener)
        return set(re.findall(r"(--[a-z0-9-]+)\s*:", css[start:css.index("}", start)]))

    def test_the_dark_palettes_cover_what_light_defines(self, css):
        light = self._block(css, ":root{\n")
        # Both dark declarations: the media query for "system dark", and the
        # explicit stamp that has to beat a light OS.
        stamped = self._block(css, ':root[data-theme="dark"]{')
        queried = self._block(css, ':root:not([data-theme="light"]){')

        # Only colours must be restated; geometry and easing are theme-neutral.
        def colourish(names):
            return {n for n in names if not re.search(
                r"radius|nav-h|ease|quick", n)}

        for name, block in (("data-theme=dark", stamped),
                            ("prefers-color-scheme:dark", queried)):
            missing = sorted(colourish(light) - colourish(block))
            assert not missing, (
                f"{name} leaves these at their light values: {missing}")

    def test_the_two_dark_palettes_agree(self, css):
        """They are written twice, so they can drift. An explicit dark choice
        and a dark OS must produce the same page."""
        stamped = self._block(css, ':root[data-theme="dark"]{')
        queried = self._block(css, ':root:not([data-theme="light"]){')
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
    """`transition:--pct` on its own does nothing at all.

    To the animation engine an unregistered custom property is an unparsed
    string, and strings do not interpolate -- so the declaration is accepted,
    inherited, and silently inert. `@property` giving it `syntax:"<number>"`
    is the whole reason it works. Measured in Chromium the ring steps
    36 -> 55 -> 68 -> 73 -> 77 -> 79 across the transition; without the
    `@property` block it jumps straight to the final value and the transition
    line is decoration.
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
    return PAGE.read_text(encoding="utf-8")


class TestTheThemeAttributeHasAWriter:
    """`[data-theme]` was read by two CSS blocks and set by nothing.

    A complete explicit-theme mechanism with no control anywhere in the app --
    the third costume of the bug this repo keeps meeting, after the measurement
    with no writer, the endpoint with no caller and the three vocabulary
    statuses nothing could set. The tell is always the same: nothing fails,
    because the *other* path (here, `prefers-color-scheme`) keeps the feature
    looking finished.
    """

    def test_something_sets_what_the_stylesheet_reads(self, page):
        css = page[page.index("<style>"):page.index("</style>")]
        assert "[data-theme=" in css, "the stylesheet no longer reads it"
        script = page[page.index("</style>"):]
        assert ("dataset.theme" in script
                or 'setAttribute("data-theme"' in script), (
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
