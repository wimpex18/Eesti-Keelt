"""The home-screen icon: `/icon.png` returns real PNG bytes (iOS ignores SVG for
`apple-touch-icon`), and the SVG mark is drawn as paths, with no font dependency.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "eesti" / "web"

#: The first eight bytes of every PNG, by specification.
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app
    return TestClient(app)


class TestTheRasterIsReallyARaster:
    def test_the_file_is_checked_in(self):
        assert (WEB / "icon.png").exists(), (
            "no icon.png is checked in")

    def test_the_route_serves_png_bytes(self, client):
        r = client.get("/icon.png")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/png")
        assert r.content.startswith(PNG_MAGIC), (
            f"/icon.png served {r.content[:16]!r}, which is not a PNG")

    def test_it_is_square_and_big_enough_to_install(self):
        """512 is what a manifest icon and an `apple-touch-icon` both want."""
        head = (WEB / "icon.png").read_bytes()[16:24]
        width, height = struct.unpack(">II", head)
        assert width == height, f"{width}x{height} — the icon must be square"
        assert width >= 192, f"{width}px is too small for a home-screen icon"


class TestTheArtworkCarriesNoFontDependency:
    def test_the_svg_draws_the_letter_rather_than_typing_it(self):
        from eesti.api.assets import ICON_SVG

        assert "<text" not in ICON_SVG, (
            "the icon types its letter in whatever font the renderer has; "
            "draw it as paths instead")
        assert "font-family" not in ICON_SVG

    def test_the_svg_is_the_cornflower(self):
        """The page's own mark: four petals round a heart, drawn as paths."""
        from eesti.api.assets import ICON_SVG

        assert ICON_SVG.count("<path") == 4 and "<circle" in ICON_SVG


class TestTheManifestOffersBoth:
    def test_it_declares_a_raster_as_well_as_the_svg(self, client):
        icons = json.loads(client.get("/manifest.webmanifest").text)["icons"]
        types = {i["type"] for i in icons}
        assert "image/png" in types, "no raster icon: iOS and some installers"
        assert "image/svg+xml" in types

    def test_the_raster_is_maskable(self, client):
        """Without `maskable` Android draws the icon inside a white circle
        instead of cropping the artwork."""
        icons = json.loads(client.get("/manifest.webmanifest").text)["icons"]
        png = [i for i in icons if i["type"] == "image/png"]
        assert png and any("maskable" in i.get("purpose", "") for i in png)
