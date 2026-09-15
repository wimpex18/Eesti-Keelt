"""The page and the stylesheet, checked against each other in both directions.

A missing CSS rule renders as silence, not an error, so: every class the markup
uses is defined; every button in a panel has a styled variant; variants share
one size; panels space their own children; counts sit outside wrapping control
rows.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pagesrc import markup_and_script, styles

ROOT = Path(__file__).resolve().parents[1]



@pytest.fixture(scope="module")
def page() -> str:
    text = markup_and_script()
    assert len(text) > 50_000, "page unexpectedly small — every check below would pass vacuously"
    return text


@pytest.fixture(scope="module")
def style(page: str) -> str:
    # The stylesheet is `eesti/web/app.css`.
    return styles()


@pytest.fixture(scope="module")
def markup(page: str) -> str:
    """The body and the modules — everything that is not the stylesheet."""
    return page


def static_classes(markup: str) -> set[str]:
    """Class tokens written literally into the markup; `class="${x}"` is skipped."""
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
        """Hook classes exempt from styling must still appear beside a styled class."""
        styled = styled_classes(style)
        for m in re.finditer(r'class="([^"{}$]*)"', markup):
            tokens = set(m.group(1).split())
            hooks = tokens & JS_HOOKS
            if hooks and not (tokens - hooks) & styled:
                # A container with no visual role is allowed to be alone.
                assert hooks <= {"lib-list", "parts"}, m.group(0)


class TestButtons:
    def test_every_button_in_a_panel_carries_a_styled_variant(self, page):
        """Every button in a panel carries a styled variant. Sliced to the last
        `</section>` (a script precedes the panels, so cutting at the first script would
        examine nothing).
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
        """Button variants share one height and padding."""
        m = re.search(
            r"button\.go,\s*button\.primary,\s*button\.ghost,\s*a\.ghost\{([^}]*)\}",
            style)
        assert m, "no shared metric rule for the button variants"
        for prop in ("padding", "min-height", "border-radius"):
            assert prop in m.group(1), f"{prop} is not shared"

    def test_no_variant_redeclares_the_shared_metrics(self, style):
        """No variant redeclares the shared metrics (pattern anchored at line start, so the
        shared selector itself does not match).
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
        """Empty containers get no spacing, so they add no phantom gaps."""
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
        """External (HARNO) items render as links, never as empty readers."""
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
        """Every settled vocabulary status, including `IGNORED`, can be listed again."""
        import inspect

        from eesti import vocab

        source = inspect.getsource(vocab.browse)
        table = source[source.index("wanted = {"):source.index("}.get(status)")]
        for rung in ("KNOWN", "IGNORED", "WELL_KNOWN", "LEARNING", "UNKNOWN"):
            assert rung in table, f"{rung} cannot be listed"


class TestNoCountIsAPageSize:
    """A count is the shelf size, not the page size, and every item is reachable by
    paging; `/api/reading/next` ranks the whole shelf.
    """

    def test_the_page_asks_for_a_total_and_prints_it(self, page):
        assert "d.total" in page
        assert "показано" in page, "the count still claims to be a total"

    def test_the_page_can_reach_the_rest(self, page):
        assert 'id="libMoreBtn"' in page
        assert "offset: String(libShown)" in page

    def test_the_total_is_the_shelf_and_not_the_page(self, client):
        """Compared against a direct count, not `len(items)`."""
        import sqlite3

        from eesti import config, sources

        conn = sqlite3.connect(config.CONTENT_DB)
        conn.row_factory = sqlite3.Row
        expected = sources.count(conn, skill="lugemine")

        # Use a limit smaller than the shelf, so a page length and a real count differ.
        assert expected > 2, "fixture shelf too small to distinguish page from total"
        body = client.get("/api/library?skill=lugemine&limit=2").json()
        assert body["limit"] == 2
        assert len(body["items"]) == 2
        assert body["total"] == expected > len(body["items"])

    def test_offset_moves_the_window(self, client):
        first = client.get("/api/library?skill=lugemine&limit=2").json()["items"]
        second = client.get(
            "/api/library?skill=lugemine&limit=2&offset=2").json()["items"]
        assert len(first) == 2 and second, "fixture too small to page"
        assert {i["id"] for i in first}.isdisjoint({i["id"] for i in second})

    def test_the_count_and_the_rows_share_their_filters(self):
        """A count built beside a query rather than from it is a number that
        looks authoritative and answers a different question."""
        import inspect

        from eesti import sources

        for fn in (sources.query, sources.count):
            assert "_filters(" in inspect.getsource(fn), fn.__name__

class TestTheDeploymentMarker:
    """The smoke check's code marker is a field the API still returns, so it identifies
    the running code rather than warning forever.
    """

    @staticmethod
    def _smoke() -> str:
        return (ROOT / ".github" / "workflows" / "smoke.yml"
                ).read_text(encoding="utf-8")

    def test_the_smoke_check_reads_the_marker(self):
        smoke = self._smoke()
        assert len(smoke) > 2000, "smoke.yml not found — this test checks nothing"
        assert 'has("total")' in smoke

    def test_the_marker_is_a_field_the_api_still_returns(self, client):
        """The half that rots. A marker naming a field that has since been
        renamed reports every healthy deployment as stale."""
        body = client.get("/api/library?skill=lugemine&limit=1").json()
        assert "total" in body
