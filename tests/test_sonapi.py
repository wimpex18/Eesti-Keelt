"""Sõnaveeb enrichment: the module that existed and nothing called.

62 statements, zero coverage, no importer — the roadmap listed it as built and
its own docstring said it "enriches a word the learner is actually looking at".
That is the word card, and the word card had never asked it anything. The
module-level version of an endpoint with no caller.

It supplies two things Vabamorf cannot: which case a verb governs — the
`rektsioon` error tag, which is a list rather than a rule — and the muuttüüp
the Notion "Nomenid A–F" page already tracks.
"""

from __future__ import annotations

import time

import pytest

from eesti.providers import sonapi


class TestSingleLookupsOnlyIsEnforced:
    """Sõnaveeb's maintainers ask people not to batch it, and the module has
    always said so in prose. A comment does not stop `for w in words:
    lookup(w)` from running as fast as Python can issue requests."""

    def test_there_is_a_minimum_interval(self):
        assert sonapi.MIN_INTERVAL >= 1.0

    def test_a_loop_is_throttled(self, monkeypatch, tmp_path):
        calls = []

        def fake_open(url, timeout=None):
            calls.append(time.monotonic())
            raise sonapi.urllib.error.HTTPError(url, 404, "nope", {}, None)

        monkeypatch.setattr(sonapi.urllib.request, "urlopen", fake_open)
        monkeypatch.setattr(sonapi, "MIN_INTERVAL", 0.15)
        monkeypatch.setattr(sonapi, "_last_request", 0.0)

        start = time.monotonic()
        for word in ("aa", "bb", "cc"):
            sonapi.fetch(word, cache_dir=tmp_path)
        assert len(calls) == 3
        assert time.monotonic() - start >= 0.3, "three live calls were not spaced"

    def test_cache_hits_are_not_throttled(self, monkeypatch, tmp_path):
        """Throttling a free read would punish the common case."""
        (tmp_path / "sonapi").mkdir(parents=True)
        (tmp_path / "sonapi" / "kass.json").write_text("null", encoding="utf-8")
        monkeypatch.setattr(sonapi, "MIN_INTERVAL", 5.0)
        start = time.monotonic()
        for _ in range(3):
            sonapi.fetch("kass", cache_dir=tmp_path)
        assert time.monotonic() - start < 1.0

    def test_there_is_still_no_bulk_helper(self):
        """If a caller wants a thousand words the answer is Ekilex with a key,
        not a loop over this."""
        assert not any(name in dir(sonapi)
                       for name in ("lookup_many", "fetch_all", "bulk"))


class TestTheTimeoutSuitsARequestPath:
    def test_it_is_short(self):
        """This runs inside a request the learner is waiting on. Twenty seconds
        was the value while nothing called the module at all."""
        assert sonapi.TIMEOUT <= 5.0


class TestTheEndpointNeverBreaksTheWordCard:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        return TestClient(app_module.app)

    def test_an_unknown_word_is_not_an_error(self, client, monkeypatch):
        monkeypatch.setattr(sonapi, "lookup", lambda w, **k: None)
        got = client.get("/api/enrich/mitteolemasolev")
        assert got.status_code == 200 and got.json()["found"] is False

    def test_a_dead_service_is_not_an_error_either(self, client, monkeypatch):
        """An enrichment is never worth an error page, and the card must not
        vanish because a third party is down."""
        def boom(word, **kw):
            raise OSError("connection refused")

        monkeypatch.setattr(sonapi, "lookup", boom)
        got = client.get("/api/enrich/lugema")
        assert got.status_code == 200 and got.json()["found"] is False


class TestThePageAsksAboutTheLemma:
    """Sõnaveeb is a dictionary: it knows `jätkuma`, not `jätkuvad`. Sending
    the surface form returned "found: false" for every inflected word — which
    in Estonian is most of them — so the enrichment looked like it had simply
    never worked."""

    def test_the_page_sends_the_lemma(self):
        from pathlib import Path

        page = (Path(__file__).resolve().parent.parent
                / "eesti" / "web" / "index.html").read_text(encoding="utf-8")
        block = page.split("/api/enrich/")[0][-400:]
        assert "analyses[0]?.lemma" in block

    def test_it_is_fetched_separately_from_the_card(self):
        """The card must be usable before a third party answers, so this
        cannot be part of `/api/lookup`."""
        from eesti.app import app

        paths = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/api/enrich/{word}" in paths and "/api/lookup/{word}" in paths
