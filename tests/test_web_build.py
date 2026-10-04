"""The optimized assets keep cache, offline and source-checkout contracts."""
from __future__ import annotations

import gzip
import re

import pytest

from eesti.api import assets


@pytest.fixture
def compiled(tmp_path, monkeypatch):
    source = assets.WEB
    target = tmp_path / "web"
    (target / "js").mkdir(parents=True)
    (target / ".build").mkdir()
    for name in ("sw.js", "app.css"):
        (target / name).write_bytes((source / name).read_bytes())
    (target / "js/main.js").write_text("import './screen.js';")
    for name, body in (("main.js", b"console.log('bundle');"), ("app.css", b"body{margin:0}")):
        (target / ".build" / name).write_bytes(body)
        (target / ".build" / (name + ".gz")).write_bytes(gzip.compress(body))
    monkeypatch.setattr(assets, "WEB", target)
    monkeypatch.setenv("EESTI_WEB_BUILD", "1")
    return target


@pytest.mark.parametrize("path", ["/js/main.js", "/app.css"])
def test_compressed_public_assets_are_negotiated_and_revalidated(client, compiled, path):
    zipped = client.get(path, headers={"Accept-Encoding": "gzip"})
    plain = client.get(path, headers={"Accept-Encoding": "gzip;q=0"})
    assert zipped.status_code == plain.status_code == 200
    assert zipped.content == plain.content
    assert zipped.headers["content-encoding"] == "gzip"
    assert "content-encoding" not in plain.headers
    assert int(zipped.headers["content-length"]) == len(gzip.compress(plain.content))
    assert zipped.headers["vary"] == "Accept-Encoding"
    assert zipped.headers["cache-control"] == "no-cache"


def test_bundled_offline_shell_does_not_redownload_source_graph(client, compiled):
    source = client.get("/sw.js").text
    block = re.search(r"const ASSETS = \[(.*?)\];", source, re.S).group(1)
    assert re.findall(r'"(/js/[^\"]+)"', block) == ["/js/main.js"]
    assert '"/app.css"' in block
    assert 'url.pathname.startsWith("/api/")' in source


def test_source_checkout_does_not_use_a_stale_bundle(client, compiled, monkeypatch):
    monkeypatch.delenv("EESTI_WEB_BUILD")
    monkeypatch.setattr(assets, "build_version", lambda: "dev")
    assert client.get("/js/main.js").text == "import './screen.js';"
    assert '"/js/core.js"' in client.get("/sw.js").text
