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

from pagesrc import markup, markup_and_script, scripts

SW = Path(__file__).resolve().parents[1] / "eesti" / "web" / "sw.js"
JS_DIR = SW.parent / "js"


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
        page = markup_and_script()
        assert "serviceWorker" in page and "/sw.js" in page

    def test_registration_failure_is_survivable(self):
        """An app that refuses to start because an enhancement did not register
        is worse than one with no worker."""
        page = markup_and_script()
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
        page = markup_and_script()
        block = page[page.index("async function api("):][:1400]
        assert "catch" in block
        assert any("Ѐ" <= ch <= "ӿ" for ch in block)


class TestThePrecacheListAndThePageAgree:
    """The shell list and the page's own tags are two halves of one fact.

    The app was one file until this split; now the page pulls a stylesheet and
    fourteen ES modules, and the worker has to precache them or an offline open
    paints an unstyled document with no behaviour -- which looks like the app
    having broken itself rather than like being offline.

    A list of filenames kept by hand is exactly what this project has been
    bitten by (`TABS`: three of ten panels missing, and nothing failed because
    every click still produced *a* panel). It cannot be derived here -- the
    worker is a static file a browser fetches, with no build step to generate
    it -- so the two sides are checked against each other in both directions,
    which is the rule for when derivation is impossible.
    """

    @staticmethod
    def _precached(source: str) -> set[str]:
        block = re.search(r"const ASSETS = \[(.*?)\];", source, re.S).group(1)
        return set(re.findall(r'"([^"]+)"', block))

    @staticmethod
    def _requested() -> set[str]:
        page = markup()
        return set(re.findall(r'<link rel="stylesheet" href="([^"]+)"', page)) | \
               set(re.findall(r'<script type="module" src="([^"]+)"', page))

    def test_there_is_something_to_compare(self, source):
        assert self._precached(source) and self._requested()

    def test_everything_the_page_asks_for_is_precached(self, source):
        missing = self._requested() - self._precached(source)
        assert not missing, (
            f"the page loads {sorted(missing)}, which the worker does not "
            f"cache -- an installed copy opens without them")

    def test_every_module_on_disk_is_precached(self, source):
        """`main.js` is the only file the page names; the rest arrive through
        its imports, so the page cannot be the whole answer."""
        missing = {f"/js/{p.name}" for p in scripts()} - self._precached(source)
        assert not missing, f"modules the worker will not cache: {sorted(missing)}"

    def test_nothing_precached_has_gone_away(self, source):
        """The other direction: a module renamed or merged leaves a URL in the
        list that 404s, and the install swallows it silently."""
        stale = [a for a in self._precached(source)
                 if a.startswith("/js/") and not (JS_DIR / Path(a).name).exists()]
        assert not stale, f"precached files that no longer exist: {stale}"


class TestCodeIsNeverServedStale:
    """The rule the split made necessary.

    While every line of JavaScript was inside `index.html`, the navigation
    branch fetched it fresh on every load and staleness was impossible. As
    `/app.css` and `/js/*.js` -- unhashed URLs, because there is no build step
    to put a hash in a filename -- cache-first would serve last week's code
    against this week's markup until somebody remembered to bump `VERSION` in
    this file. For ever, silently, and only for the people who had already
    installed the app.
    """

    @staticmethod
    def _code_branch(source: str) -> str:
        start = source.index('url.pathname === "/app.css"')
        return source[start:start + 900]

    def test_the_page_code_is_matched_before_the_cache_first_branch(self, source):
        code_at = source.index('url.pathname === "/app.css"')
        cache_first_at = source.index("const cached = await caches.match(request);\n    if (cached) return cached;")
        assert code_at < cache_first_at, (
            "the cache-first branch answers first, so app code is served stale")

    def test_it_asks_the_network_first(self, source):
        branch = self._code_branch(source)
        assert branch.index("await fetch(request)") < branch.index("caches.match"), (
            "app code must be fetched before the cache is consulted")

    def test_a_successful_answer_replaces_what_was_cached(self, source):
        assert "cache.put(request, res.clone())" in self._code_branch(source)

    def test_offline_still_gets_the_last_good_copy(self, source):
        """Network-first must not mean network-only: an installed app has to
        open with no connection, which is the whole reason for the worker."""
        branch = self._code_branch(source)
        assert "catch" in branch and "caches.match(request)" in branch

    def test_the_modules_are_still_precached(self, source):
        """Network-first fills the cache on a successful load, but a first run
        that goes offline before opening a panel would have nothing. The
        install step still puts them there."""
        assert "/js/main.js" in source and "/app.css" in source


class TestTheCacheVersionIsDerived:
    """The version string is the only thing that retires an old shell.

    `activate` deletes every cache whose name is not the current one, so while
    `VERSION` was a literal somebody had to remember to edit, a redeploy that
    did not edit it kept the previous `index.html` on disk for ever — and that
    page names the modules it loads. A hand-bumped version is a hand-maintained
    list of one.
    """

    @pytest.fixture
    def served(self, client):
        return client.get("/sw.js").text

    def test_the_file_still_declares_the_line_that_gets_stamped(self, source):
        from eesti.api.assets import _VERSION_LINE

        assert _VERSION_LINE in source

    def test_a_source_checkout_says_dev(self, served):
        """No build info, nothing to retire: the file on disk is the file being
        served."""
        assert 'const VERSION = "dev";' in served

    def test_a_build_stamps_its_revision(self, client, monkeypatch):
        from eesti.api import deps

        monkeypatch.setattr(deps, "BUILD", {"built": "2026-09-01", "revision": "abc1234"})
        assert 'const VERSION = "abc1234";' in client.get("/sw.js").text

    def test_the_build_date_is_the_fallback(self, client, monkeypatch):
        from eesti.api import deps

        monkeypatch.setattr(deps, "BUILD", {"built": "2026-09-01T10:00:00Z", "revision": None})
        assert 'const VERSION = "2026-09-01T10:00:00Z";' in client.get("/sw.js").text

    def test_a_renamed_line_fails_loudly(self, monkeypatch):
        """A silent no-op here brings back exactly the bug this prevents."""
        from eesti.api import assets

        monkeypatch.setattr(assets, "_VERSION_LINE", 'const VERSION = "moved";')
        with pytest.raises(RuntimeError, match="cache version"):
            assets.worker_source()

    def test_two_builds_do_not_share_a_cache(self, client, monkeypatch):
        from eesti.api import deps

        monkeypatch.setattr(deps, "BUILD", {"revision": "aaa", "built": None})
        first = client.get("/sw.js").text
        monkeypatch.setattr(deps, "BUILD", {"revision": "bbb", "built": None})
        assert client.get("/sw.js").text != first


class TestTheOfflineShellTracksDeploys:
    def test_a_successful_navigation_updates_the_cached_page(self, source):
        """Without this the cached shell is whatever `install` fetched and
        never changes again inside one version, so the page served offline can
        name modules the deployment has since renamed."""
        branch = source[source.index('request.mode === "navigate"'):][:800]
        assert "cache.put(\"/\"" in branch, (
            "the navigation branch does not refresh the cached shell")

    def test_it_still_only_stores_a_clean_answer(self, source):
        branch = source[source.index('request.mode === "navigate"'):][:800]
        assert "res.ok && !res.redirected && res.type === \"basic\"" in branch
