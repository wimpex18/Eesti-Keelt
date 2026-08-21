"""The PWA installed and then needed the network.

`manifest.webmanifest` has been served for months, so the app was installable,
and nothing backed that up: an installed copy failed exactly like a browser tab
with the signal off. Half a claim is worse than none.

These tests pin the three rules that make the worker safe rather than the fact
that it exists, because the dangerous version of this feature is the one that
caches something it should not:

  * **the API is never cached** — every endpoint is either the learner's own
    state or freshly generated, and a drill that is quietly a day old is worse
    than one that is unavailable;
  * **nothing that is not a clean 200 is stored** — Cloudflare Access answers a
    signed-out request with a 302 to a login page, and caching that would pin
    the login screen in front of the app until someone cleared site data;
  * **the offline text is Russian** — it is the only thing on screen when it
    appears, so it has to be readable by the person reading it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SW = Path(__file__).resolve().parents[1] / "eesti" / "web" / "sw.js"
PAGE = Path(__file__).resolve().parents[1] / "eesti" / "web" / "index.html"


@pytest.fixture(scope="module")
def source() -> str:
    return SW.read_text(encoding="utf-8")


@pytest.fixture
def client():
    """No learner state needed: `/sw.js` reads one file off disk. Importing
    `eesti.app` opens no database, which is what makes this safe to do without
    the redirect fixtures."""
    from fastapi.testclient import TestClient

    from eesti import app as app_module

    return TestClient(app_module.app)


class TestItIsServedAtAllAndFromTheRoot:
    def test_the_file_exists(self):
        assert SW.exists()

    def test_the_route_serves_javascript(self, client):
        """A worker served as anything but JavaScript is rejected outright."""
        r = client.get("/sw.js")
        assert r.status_code == 200
        assert "javascript" in r.headers["content-type"]

    def test_it_is_not_http_cached(self, client):
        """A worker pinned by HTTP caching cannot be replaced, which is the
        failure where a bad worker outlives the deploy that fixes it."""
        assert "no-cache" in client.get("/sw.js").headers.get("cache-control", "")

    def test_the_page_registers_it(self):
        page = PAGE.read_text(encoding="utf-8")
        assert "serviceWorker" in page and "/sw.js" in page

    def test_registration_failure_is_survivable(self):
        """An app that refuses to start because an enhancement did not register
        is worse than one with no worker."""
        page = PAGE.read_text(encoding="utf-8")
        block = page[page.index('navigator.serviceWorker.register'):][:120]
        assert ".catch(" in block


class TestTheApiIsNeverCached:
    def test_api_requests_are_passed_straight_through(self, source):
        assert 'url.pathname.startsWith("/api/")' in source
        # The guard must `return` before any caching path, not fall through
        # into one.
        guard = source[source.index('url.pathname.startsWith("/api/")'):][:80]
        assert "return" in guard

    def test_no_cache_call_mentions_an_api_path(self, source):
        for call in re.findall(r"cache\.put\([^)]*\)", source):
            assert "/api/" not in call

    def test_the_precache_list_holds_no_api_paths(self, source):
        assets = re.search(r"ASSETS\s*=\s*\[(.*?)\]", source, re.S).group(1)
        assert "/api/" not in assets


class TestOnlyCleanResponsesAreStored:
    def test_a_redirect_is_never_cached(self, source):
        """Access answers a signed-out request with a 302 to a login page."""
        assert "redirected" in source
        assert source.count("!res.redirected") >= 2

    def test_only_ok_responses_are_cached(self, source):
        assert "res.ok" in source

    def test_only_get_is_intercepted(self, source):
        """Replaying a POST from a cache would record an answer the learner
        never gave."""
        assert 'request.method !== "GET"' in source

    def test_only_this_origin_is_intercepted(self, source):
        assert "url.origin !== self.location.origin" in source


class TestItDoesNotOutliveItsOwnDeploy:
    def test_old_caches_are_deleted_on_activate(self, source):
        assert "caches.delete" in source
        assert "activate" in source

    def test_the_cache_name_carries_a_version(self, source):
        assert re.search(r"VERSION\s*=", source)
        assert re.search(r"SHELL\s*=\s*`shell-\$\{VERSION\}`", source)


class TestTheOfflineTextIsReadable:
    def test_it_is_russian(self, source):
        page = source[source.index("OFFLINE_PAGE"):]
        assert any("Ѐ" <= ch <= "ӿ" for ch in page)

    def test_it_does_not_promise_offline_exercises(self, source):
        """Drills are generated on the server. Saying otherwise would send the
        learner looking for something that cannot be there."""
        page = source[source.index("OFFLINE_PAGE"):]
        assert "сервере" in page

    def test_the_page_says_the_same_thing_when_a_fetch_fails(self):
        """The browser's own TypeError message is English — "Failed to fetch" —
        and every caller renders it into a banner, so with no connection the
        app told a Russian-speaking learner exactly that. Made reachable by the
        worker: before it, the browser's offline page showed instead and the
        app never got to speak."""
        page = PAGE.read_text(encoding="utf-8")
        block = page[page.index("async function api("):][:1400]
        assert "catch" in block
        assert any("Ѐ" <= ch <= "ӿ" for ch in block)
