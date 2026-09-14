"""Playing HLS audio in browsers without native support.

Many ERR audio items are HLS streams (`.m3u8`): Safari plays them natively,
Chrome and Firefox need hls.js. These pin the properties that make playback work
(checked in source; a browser is not in CI).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pagesrc import markup_and_script

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "eesti" / "web" / "vendor"


@pytest.fixture(scope="module")
def page() -> str:
    return markup_and_script()


class TestHlsFallback:
    def test_the_library_is_vendored_not_fetched_from_a_cdn(self):
        """hls.js is served locally, not from a CDN."""
        assert (VENDOR / "hls.light.min.js").is_file()

    def test_the_page_loads_it_from_here(self, page):
        assert "/vendor/hls.light.min.js" in page
        assert "cdn." not in page.split("<script")[0]

    def test_native_playback_is_preferred(self, page):
        """Safari plays HLS without help, and loading a library to duplicate
        what the browser already does is pure cost."""
        assert "canPlayType" in page
        assert "application/vnd.apple.mpegurl" in page

    def test_it_is_loaded_lazily(self, page):
        """Verified in a browser: `window.Hls` is undefined at page load and
        defined only after an HLS stream is opened. A learner who never touches
        the radio archive never downloads 290 KB."""
        assert "function loadHls" in page
        assert not re.search(r'<script[^>]+hls\.light', page)

    def test_failure_is_announced_rather_than_silent(self, page):
        """A playback failure shows a message."""
        block = page.split("async function mountAudio")[1][:1400]
        assert "catch" in block
        assert any("Ѐ" <= ch <= "ӿ" for ch in block), (
            "the message explaining a dead player must be readable by a "
            "Russian speaker still learning Estonian"
        )


class TestVideo:
    def test_embeds_avoid_the_tracking_cookie(self, page):
        """An app behind a private login should not hand a third party a cookie
        on page load, and the embed works identically without one."""
        assert "youtube-nocookie.com" in page
        assert "www.youtube.com/embed" not in page

    def test_the_id_is_extracted_from_both_url_shapes(self, page):
        """`youtu.be/ID` and `watch?v=ID` both appear on harno.ee."""
        assert "youtu\\.be" in page or "youtu.be" in page
        assert "v=" in page.split("const YT")[1][:120]


class TestTheVendorRoute:
    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        return TestClient(app_module.app)

    def test_it_serves_the_library(self, client):
        response = client.get("/vendor/hls.light.min.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]

    def test_a_missing_file_is_a_404(self, client):
        assert client.get("/vendor/nope.js").status_code == 404

    @pytest.mark.parametrize("attack", [
        "../app.py", "..%2fapp.py", "....//app.py", "/etc/passwd",
    ])
    def test_it_refuses_to_leave_its_directory(self, client, attack):
        """`name` comes straight off the URL."""
        assert client.get(f"/vendor/{attack}").status_code in (404, 400)


class TestTheVendoredPlayerSaysWhatItIs:
    """The vendored hls.js records its version beside the file, checked against the
    bundle.
    """

    VERSION = ROOT / "eesti" / "web" / "vendor" / "hls.js.version"
    BUNDLE = ROOT / "eesti" / "web" / "vendor" / "hls.light.min.js"

    def test_the_version_is_recorded(self):
        assert self.VERSION.exists(), (
            "nothing records which hls.js this is; the next person has to grep "
            "a minified bundle for a semver-shaped string")
        assert re.fullmatch(r"\d+\.\d+\.\d+", self.VERSION.read_text().strip())

    def test_the_bundle_agrees_with_the_record(self):
        """The record is only worth having if it describes the file beside it."""
        recorded = self.VERSION.read_text(encoding="utf-8").strip()
        source = self.BUNDLE.read_text(encoding="utf-8", errors="replace")
        assert f'"{recorded}"' in source, (
            f"the file records {recorded} and the bundle does not contain that "
            f"version string")

    def test_the_page_asks_for_it_by_the_path_that_is_served(self, page):
        assert "/vendor/hls.light.min.js" in page
