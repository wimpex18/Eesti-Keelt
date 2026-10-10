"""The shell's colours outside the page: the installed app and the offline page.

An installed app paints its splash screen and status bar from the manifest, and
a first run with no connection shows the service worker's own page. Both must
meet the page they lead to on its ground (DESIGN.md, the frontmatter being the
tokens' one source), or the learner sees the earlier pale blue flash before
the birch ground, or a fallback page from another app.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def tokens() -> dict:
    front = (ROOT / "DESIGN.md").read_text(encoding="utf-8").split("---")[1]
    return yaml.safe_load(front)["colors"]


class _Metas(HTMLParser):
    def __init__(self, page: str):
        super().__init__()
        self.theme: dict[str, str] = {}
        self.requests: list[str] = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") == "theme-color":
            scheme = "dark" if "dark" in (a.get("media") or "") else "light"
            self.theme[scheme] = a["content"].upper()
        for key in ("src", "href"):
            if a.get(key) and tag != "a":
                self.requests.append(a[key])


def _theme(html: str) -> dict[str, str]:
    return _Metas(html).theme


def _offline_page(source: str) -> str:
    return re.search(r"const OFFLINE_PAGE = `(.*?)`;", source, re.S).group(1)


def test_the_page_names_the_ground_of_both_themes(client, tokens):
    assert _theme(client.get("/").text) == {
        "light": tokens["ground"].upper(), "dark": tokens["dark-ground"].upper()}


def test_an_installed_app_opens_on_the_same_ground(client):
    manifest = client.get("/manifest.webmanifest").json()
    light = _theme(client.get("/").text)["light"]
    assert manifest["background_color"].upper() == manifest["theme_color"].upper() == light


def test_the_offline_page_is_on_the_same_ground(client):
    offline = _offline_page(client.get("/sw.js").text)
    assert _theme(offline) == _theme(client.get("/").text)
    # Its own colours, light and dark, are the grounds it announces.
    for ground in _theme(offline).values():
        assert ground.lower() in offline.lower()


def test_the_offline_page_asks_for_nothing(client):
    """It is shown because nothing could be fetched; a font, icon or stylesheet it
    asked for would not arrive either."""
    offline = _offline_page(client.get("/sw.js").text)
    assert not _Metas(offline).requests
    assert "url(" not in offline
