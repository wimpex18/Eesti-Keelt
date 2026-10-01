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

    def test_each_declared_install_icon_is_served_at_its_declared_size(self, client):
        """An installer must get the declared artwork, rather than a 404 or a
        mislabeled raster; Android's maskable glyph must survive the safe crop.
        """
        from io import BytesIO
        from PIL import Image

        icons = client.get("/manifest.webmanifest").json()["icons"]
        for item in icons:
            response = client.get(item["src"])
            assert response.status_code == 200
            assert response.headers["content-type"].startswith(item["type"])
            if item["type"] == "image/png":
                image = Image.open(BytesIO(response.content)).convert("RGBA")
                width, height = map(int, item["sizes"].split("x"))
                assert image.size == (width, height)
                if item["purpose"] == "maskable":
                    assert image.getextrema()[3] == (255, 255)
                    white = [(x, y) for y in range(height) for x in range(width)
                             if min(image.getpixel((x, y))[:3]) > 240]
                    assert white
                    assert all((x-width/2)**2 + (y-height/2)**2 <= (.4*width)**2
                               for x, y in white)

    def test_apple_and_favicon_conventional_urls_work(self, client):
        from io import BytesIO
        from PIL import Image

        assert Image.open(BytesIO(client.get("/apple-touch-icon.png").content)).size == (180, 180)
        ico = Image.open(BytesIO(client.get("/favicon.ico").content))
        assert ico.ico.sizes() == {(16, 16), (32, 32), (48, 48)}

    def test_social_images_use_the_serving_origin_locally(self, client):
        response = client.get("/", headers={"x-brand-origin": "https://forged.test"})
        assert 'content="http://testserver/brand/og-default.png"' in response.text
        assert "forged.test" not in response.text

    def test_social_images_use_the_guarded_front_door(self, client, monkeypatch):
        monkeypatch.setenv("PROXY_TOKEN", "test-token")
        response = client.get("/", headers={"x-proxy-token": "test-token",
                                            "x-brand-origin": "https://learn.example"})
        assert response.status_code == 200
        assert 'content="https://learn.example/brand/og-default.png"' in response.text
        assert client.get("/brand/og-default.png", headers={"x-proxy-token": "test-token"}).content.startswith(PNG_MAGIC)
