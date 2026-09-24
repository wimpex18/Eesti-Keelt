"""The typefaces are the app's own files.

A face the stylesheet names but the server does not serve falls back to the
system font without a word: the Estonian material would lose its serif and
nothing would fail. Served from this origin, the installed app keeps its type
offline and the page asks no font host for anything.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "eesti" / "web"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from eesti.app import app
    return TestClient(app)


def _font_urls() -> list[str]:
    css = (WEB / "app.css").read_text(encoding="utf-8")
    return re.findall(r'url\("(/fonts/[^"]+)"\)', css)


def test_the_stylesheet_names_its_faces():
    assert len(_font_urls()) >= 2, "no self-hosted face is declared"


@pytest.mark.parametrize("url", _font_urls())
def test_every_face_it_names_is_served(client, url):
    r = client.get(url)
    assert r.status_code == 200, url
    assert r.headers["content-type"] == "font/woff2"
    assert r.content[:4] == b"wOF2", f"{url} is not a WOFF2 file"


def test_the_page_asks_no_font_host():
    page = (WEB / "index.html").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in page and "fonts.gstatic.com" not in page


def test_a_path_outside_the_folder_is_refused(client):
    assert client.get("/fonts/..%2Fapp.css").status_code == 404
    assert client.get("/fonts/OFL-Onest.txt").status_code == 404


def test_each_face_carries_its_licence():
    """SIL OFL 1.1 requires the licence to travel with the font."""
    for face in ("Onest", "Literata"):
        text = (WEB / "fonts" / f"OFL-{face}.txt").read_text(encoding="utf-8")
        assert "SIL Open Font License" in text
