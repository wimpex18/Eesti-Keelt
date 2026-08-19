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
