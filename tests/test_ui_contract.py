"""The interface asks for things; this checks the API serves them.

A whole suite passed while the reading list returned zero texts for every
difficulty. The cause was a rename: relative bands moved out of the `level`
column into their own, and the `<select>` went on sending `level=kergem`. The
API answered honestly — no item has that level any more — and the page showed
an empty list with no error.

Nothing caught it because the two halves are tested separately. `library()` was
asked for `band` and answered; the page sent `level` and nobody asked what the
page sent. This is the seam, and it is where the last three UI bugs have been:
the POST-only fetch helper, the `role="tab"` mismatch, and this.

The approach is deliberately blunt — read the page, pull out what it queries,
and demand the API accepts it. A cleverer test would have the same blind spot
as the code.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("httpx", reason="TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402

PAGE = Path(__file__).resolve().parent.parent / "eesti" / "web" / "index.html"


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(app_module, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(app_module, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.setattr(app_module, "NOTION_DB", str(tmp_path / "n.db"))
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


def api_paths(page: str) -> set[str]:
    """Every `/api/...` literal the page fetches, normalised to a route shape.

    Two ways the page builds a URL, and both have to survive normalisation:
    a template literal (`/api/exam/${level}`) and plain concatenation
    (`"/api/lookup/" + word`). A trailing slash means the value follows, so it
    becomes a parameter rather than being trimmed away — trimming it turned
    `/api/lookup/` into `/api/lookup` and reported a route that exists as
    missing.
    """
    found = set(re.findall(r'["`\'](/api/[^"`\'?\s]+)', page))
    out = set()
    for path in found:
        path = re.sub(r"\$\{[^}]*\}", "{x}", path)
        out.add(path[:-1] + "/{x}" if path.endswith("/") else path)
    return out


class TestEveryEndpointThePageCallsExists:
    def test_no_call_is_to_a_route_that_does_not_exist(self, page):
        """A typo or a renamed route shows as an empty panel, never an error."""
        routes = {
            re.sub(r"\{[^}]+\}", "{x}", r.path).rstrip("/")
            for r in app_module.app.routes if hasattr(r, "path")
        }
        for path in api_paths(page):
            assert path in routes, f"the page calls {path}, which is not a route"


class TestQueryParametersAreAccepted:
    """The bug that made this file: the page sent a parameter the API had
    stopped using, and got an empty list rather than a complaint."""

    @pytest.mark.parametrize("query", [
        "/api/library?skill=lugemine&limit=80",
        "/api/library?skill=lugemine&band=kergem&limit=80",
        "/api/library?skill=eksam&limit=40",
        "/api/reading/next?limit=25",
    ])
    def test_the_reading_views_are_served(self, client, query):
        assert client.get(query).status_code == 200

    def test_the_difficulty_filter_uses_the_column_it_lives_in(self, page):
        """`band`, not `level`. They were one column and are now two, and the
        page kept sending the name that no longer selects anything."""
        loader = page.split("async function loadLibrary")[1][:1600]
        assert 'q.set("band"' in loader
        assert 'q.set("level"' not in loader

    def test_the_selector_offers_the_recommendation_first(self, page):
        """It is the only option that knows anything about *this* reader; the
        rest rank texts against each other."""
        options = page.split('id="readLevel"')[1][:600]
        first = re.search(r'<option value="([^"]*)"', options).group(1)
        assert first == "soovitatud"


class TestVerbsMatch:
    def test_endpoints_the_page_posts_to_accept_post(self, client):
        for path, body in [("/api/check", {"text": "Tere"}),
                           ("/api/notion/queue", {"wrong": "a", "correct": "b",
                                                  "tag": "obj-case"})]:
            assert client.post(path, json=body).status_code in (200, 400)

    def test_endpoints_the_page_gets_do_not_require_a_body(self, client):
        """The fetch helper was POST-only, and posting to a GET route produces
        a 405 that looks exactly like a feature quietly not working."""
        for path in ("/api/modes", "/api/readiness/A2", "/api/exam/A2",
                     "/api/reading/next"):
            assert client.get(path).status_code == 200, path


class TestTheDesktopRail:
    """A MacBook is the other half of this app. The rail is what fills the
    300px a phone does not have — countdown, resume point, untouched exam
    parts — and it broke once in a way no API test could see: the base
    `.rail{display:none}` sat *after* the media query, same specificity, so
    the later rule won and the rail was invisible at every width while still
    fetching and rendering into itself."""

    def test_the_hiding_rule_comes_before_the_query_that_undoes_it(self, page):
        hide = page.index(".rail{display:none}")
        query = page.index("@media (min-width:1080px)")
        assert hide < query, (
            "`.rail{display:none}` must precede the media query; at equal "
            "specificity the later declaration wins and the rail disappears"
        )

    def test_the_query_turns_the_rail_back_on(self, page):
        block = page[page.index("@media (min-width:1080px)"):][:700]
        assert "display:flex" in block.split(".rail{")[1]

    def test_the_countdown_follows_the_level_the_learner_picked(self, page):
        """Hardcoding a level here would have shown B1's countdown while the
        rest of the page was on A2 — and A2 is the nearer decision."""
        fn = page.split("async function loadRail")[1][:900]
        assert "/api/readiness/${examLevel}" in fn
        assert "/api/readiness/B1" not in fn
        assert "/api/readiness/A2" not in fn

    def test_the_rail_is_refreshed_when_what_it_shows_changes(self, page):
        """Mastered topics and due reviews both move during a session. A rail
        that only renders on load is a wrong number sitting in the corner."""
        assert page.count("loadRail()") >= 4  # load, level switch, path, review


class TestEveryTabOpensItsOwnPanel:
    """Found by opening the app on a laptop: clicking `Kirjutamine` left the
    path panel on screen.

    `TABS` was a hand-written list of panel names and it had drifted from the
    document — `path`, `speak` and `status` were missing. `selectTab` only
    hides what the list names, so `#tab-path` was never hidden (it showed
    underneath every other tab) and `#tab-speak` and `#tab-status` were never
    unhidden (the speaking practice and the progress view could not be opened
    at all). Nothing failed: every click still produced a panel, just not the
    one asked for.

    The fix derives the set from the panels themselves. These tests hold the
    two halves together whichever way the next section is added."""

    def panels(self, page: str) -> set[str]:
        return set(re.findall(r'id="tab-([a-z]+)"', page))

    def buttons(self, page: str) -> set[str]:
        return set(re.findall(r'data-tab="([a-z]+)"', page))

    def test_every_button_has_a_panel(self, page):
        missing = self.buttons(page) - self.panels(page)
        assert not missing, f"tabs with no panel: {sorted(missing)}"

    def test_every_panel_has_a_button(self, page):
        """An orphan panel is one that shows and never hides, because nothing
        ever selects a different tab within its group."""
        missing = self.panels(page) - self.buttons(page)
        assert not missing, f"panels no tab opens: {sorted(missing)}"

    def test_the_switch_set_is_read_from_the_document(self, page):
        """A literal list is what drifted. Deriving it makes adding a section
        sufficient."""
        decl = page.split("const TABS =")[1][:220]
        assert "querySelectorAll" in decl, (
            "TABS must be derived from the panels in the document, not "
            "hand-listed — the hand-listed version silently lost three panels"
        )

    def test_exactly_one_panel_starts_visible(self, page):
        """Two unhidden panels stack on load; zero shows a blank app."""
        sections = re.findall(r'<section class="panel" id="tab-[a-z]+"([^>]*)>', page)
        assert sum("hidden" not in s for s in sections) == 1
