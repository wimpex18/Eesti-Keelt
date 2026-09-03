"""The mark on the home screen, and the two ways it was not there.

`/icon.png` existed as a route and returned SVG bytes: no PNG file had ever
been checked in, and the handler fell back to `ICON_SVG` under a `.png` name.
The one platform that fallback was written for is the one that cannot use it
-- iOS ignores SVG for `apple-touch-icon`, which the handler's own docstring
said -- so adding the app to a home screen produced a screenshot of the page
rather than the icon. A route returning 200 is not the same as a route
returning what it claims, and nothing here was checking the bytes.

The second failure was inside the artwork. The `ä` was a `<text>` element in a
system font stack, which is a font dependency inside an icon: the glyph is
drawn by whichever face the renderer resolves, so it changes weight and
metrics between platforms and can be missing entirely from a rasteriser's
environment. An icon has to be the same picture everywhere it is pasted.
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
            "no icon.png — the route used to paper over this by serving SVG")

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

    def test_the_svg_is_still_the_estonian_letter(self):
        """Strokes, not a wordmark: a bowl, a stem and two dots."""
        from eesti.api.assets import ICON_SVG

        assert ICON_SVG.count("<path") >= 3 and "<circle" in ICON_SVG


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
