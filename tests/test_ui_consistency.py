"""The page and the stylesheet, checked against each other in both directions.

Every defect in here was found by opening the app and looking at it, and none
of them failed a test — because each was a *missing* rule rather than a wrong
one, and a browser renders a missing rule as silence. A class with no CSS is
the same shape of bug as an endpoint with no caller and a measurement with no
writer: the markup names something, nothing answers, and every screen still
draws.

What was actually found, on 2026-08-22, at 1440px and 390px:

- `.primary` appeared in the hover and border rules as though it were an alias
  of `.go`, and had no base rule at all. `Näita` in Sõnavara rendered as a bare
  operating-system button wearing a 3px green underline.
- `#vocMoreBtn` carried no class whatsoever — the only such button in a panel.
- `.note` was used three times and defined nowhere, so the paragraph explaining
  the vocabulary screen rendered at full body weight.
- `textarea` had no top margin while `.row` had one, so the dictation box sat
  flush against the ▶ Kuula row above it.
- `#libCount` lived *inside* the control row, which wraps, so the same number
  rendered beside the button when it was short and under it when it was long.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "eesti" / "web" / "index.html"


@pytest.fixture(scope="module")
def page() -> str:
    text = PAGE.read_text(encoding="utf-8")
    assert len(text) > 50_000, "page unexpectedly small — every check below would pass vacuously"
    return text


@pytest.fixture(scope="module")
def style(page: str) -> str:
    return page[page.index("<style>"):page.index("</style>")]


@pytest.fixture(scope="module")
def markup(page: str) -> str:
    """Everything after the stylesheet: the body, and the scripts in it."""
    return page[page.index("</style>"):]


def static_classes(markup: str) -> set[str]:
    """Class tokens written literally into the markup.

    Attributes holding a template expression are skipped rather than parsed:
    `class="${x}"` names no class this can check.
    """
    out: set[str] = set()
    for m in re.finditer(r'class="([^"{}$]*)"', markup):
        out.update(m.group(1).split())
    return out


def styled_classes(style: str) -> set[str]:
    return set(re.findall(r"\.([A-Za-z][\w-]*)", style))


#: Classes that are hooks for script, not appearances. Each is paired in the
#: markup with a class that *is* styled, so the element is never unstyled —
#: which is the only reason an exemption is safe.
JS_HOOKS = {"fc-note", "fc-show", "lib-list", "mine-note", "parts"}


class TestEveryClassInTheMarkupHasARule:
    def test_there_are_classes_to_check(self, markup):
        assert len(static_classes(markup)) > 40

    def test_no_class_is_named_and_never_defined(self, style, markup):
        orphans = static_classes(markup) - styled_classes(style) - JS_HOOKS
        assert not orphans, f"used in markup, defined nowhere: {sorted(orphans)}"

    def test_the_hook_exemptions_are_still_paired_with_a_styled_class(
            self, style, markup):
        """An exemption that stops being paired stops being safe.

        `lib-list` is a bare container and `parts` a wrapper; the rest sit
        beside `hint`, `go` or `no`. If one is ever used alone it is an
        unstyled element again, and this list would be hiding it.
        """
        styled = styled_classes(style)
        for m in re.finditer(r'class="([^"{}$]*)"', markup):
            tokens = set(m.group(1).split())
            hooks = tokens & JS_HOOKS
            if hooks and not (tokens - hooks) & styled:
                # A container with no visual role is allowed to be alone.
                assert hooks <= {"lib-list", "parts"}, m.group(0)


class TestButtons:
    def test_every_button_in_a_panel_carries_a_styled_variant(self, page):
        """`#vocMoreBtn` had no class and rendered as an OS button.

        Sliced to the *last* `</section>`, not to the first `<script>`. The
        theme pre-paint block runs immediately after `<body>` and before every
        panel, so cutting at the first script produced a zero-length string and
        a test that passed by examining nothing. This repo has now written that
        exact bug twice; the guard below is why the second one lasted minutes.
        """
        body = page[page.index('<section class="panel"'):page.rindex("</section>")]
        assert body.count("<button") > 15, "panel slice is wrong — nothing checked"
        variants = {"go", "primary", "ghost"}
        bad = []
        for m in re.finditer(r"<button\b([^>]*)>", body):
            attrs = m.group(1)
            if 'role="tab"' in attrs:          # nav and level tabs style themselves
                continue
            classes = set(re.findall(r'class="([^"]*)"', attrs))
            tokens = set(" ".join(classes).split())
            if not tokens & variants:
                bad.append(m.group(0))
        assert not bad, f"buttons with no styled variant: {bad}"

    def test_the_variants_share_one_size(self, style):
        """`.go` was 11/20 at 44px and `.ghost` 9/15 at 40px, so a row holding
        one of each was visibly ragged and the green one read as oversized."""
        m = re.search(
            r"button\.go,\s*button\.primary,\s*button\.ghost,\s*a\.ghost\{([^}]*)\}",
            style)
        assert m, "no shared metric rule for the button variants"
        for prop in ("padding", "min-height", "border-radius"):
            assert prop in m.group(1), f"{prop} is not shared"

    def test_no_variant_redeclares_the_shared_metrics(self, style):
        """A second `padding` on one variant is how they drift apart again.

        Anchored at the start of a line, because `button.ghost, a.ghost{` is
        also the tail of the shared selector and an unanchored pattern matches
        the very rule it is meant to be checking against.
        """
        for sel in (r"^\s*button\.go, button\.primary\{",
                    r"^\s*button\.ghost, a\.ghost\{"):
            found = re.findall(sel + r"([^}]*)\}", style, re.M)
            assert found, sel
            for body in found:
                assert "padding" not in body, body
                assert "min-height" not in body, body


class TestFlowSpacing:
    def test_a_panel_spaces_its_own_children(self, style):
        """The rule that stops the next element type with no margin of its own
        from sitting flush against its neighbour."""
        assert ".panel > * + *:not(:empty){margin-top:" in style

    def test_empty_containers_are_excluded(self, style):
        """A panel is full of containers that hold nothing until something is
        rendered into them; spacing those stacks phantom gaps down the page."""
        rule = re.search(r"\.panel > \* \+ \*([^{]*)\{", style)
        assert rule and ":not(:empty)" in rule.group(1)

    def test_the_first_child_is_still_flush(self, style):
        assert ".panel > :first-child{margin-top:0}" in style


class TestTheReadingList:
    def test_the_count_is_not_inside_the_control_row(self, page):
        """`.row` wraps, so a hint inside it moves when its text grows."""
        row = re.search(
            r'<div class="row">(?:(?!</div>).)*id="loadLib".*?</div>',
            page, re.S)
        assert row, "could not find the Lugemine control row"
        assert 'id="libCount"' not in row.group(0)

    def test_the_list_branches_on_external(self, page):
        """HARNO's tasks are indexed, never copied: `body` is empty by licence.
        Rendered like a text, one advertised "0 слов" and opened an empty
        reader. The API has carried `external` and the url since it was
        written; the page had never read either."""
        assert "it.external" in page
        assert re.search(r"if \(it\.external\)", page)


class TestTheVocabularyFilters:
    def test_every_status_the_page_offers_is_one_the_store_accepts(self, page):
        """Two-way: a select option nothing accepts is a 422 waiting to happen,
        and a status the store knows with no option is a rung the learner can
        set and never list again."""
        import inspect

        from eesti import vocab

        block = re.search(r'<select id="vocStatus">(.*?)</select>', page, re.S)
        assert block, "no status filter on the page"
        offered = {v for v in re.findall(r'value="([^"]*)"', block.group(1)) if v}

        source = inspect.getsource(vocab.browse)
        table = source[source.index("wanted = {"):source.index("}.get(status)")]
        accepted = set(re.findall(r'"(\w+)":', table))

        assert offered <= accepted, f"offered, not accepted: {sorted(offered - accepted)}"
        assert accepted <= offered, f"accepted, never offered: {sorted(accepted - offered)}"

    def test_every_settled_rung_can_be_listed_again(self):
        """`IGNORED` is set by "Pole vaja" and used to have no filter at all,
        so removing a word from study could not be undone through the only
        surface that does it."""
        import inspect

        from eesti import vocab

        source = inspect.getsource(vocab.browse)
        table = source[source.index("wanted = {"):source.index("}.get(status)")]
        for rung in ("KNOWN", "IGNORED", "WELL_KNOWN", "LEARNING", "UNKNOWN"):
            assert rung in table, f"{rung} cannot be listed"
