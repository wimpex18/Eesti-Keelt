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

from pagesrc import markup_and_script


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


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client whose stores are its own.

    Without the redirect these tests wrote glosses into the developer's real
    `data/vocab.db` -- and then read them back, so "the service is down" still
    returned found:true because an earlier test in the same file had cached the
    word. A path opened inside a function cannot be redirected by its caller;
    the caller has to point the module constant somewhere else.
    """
    from fastapi.testclient import TestClient

    from eesti import app as app_module

    monkeypatch.setattr(app_module, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(app_module, "REVIEW_DB", str(tmp_path / "r.db"))
    return TestClient(app_module.app)


class TestTheEndpointNeverBreaksTheWordCard:

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
        # A word the shipped glossary does not carry. `lugema` used to be here
        # and is seeded now, so the store answered and the dead service was
        # never reached -- which tested the seed rather than this path.
        got = client.get("/api/enrich/seinamaaling")
        assert got.status_code == 200 and got.json()["found"] is False


class TestThePageAsksAboutTheLemma:
    """Sõnaveeb is a dictionary: it knows `jätkuma`, not `jätkuvad`. Sending
    the surface form returned "found: false" for every inflected word — which
    in Estonian is most of them — so the enrichment looked like it had simply
    never worked."""

    def test_the_page_sends_the_lemma(self):
        from pathlib import Path

        page = markup_and_script()
        block = page.split("/api/enrich/")[0][-400:]
        assert "analyses[0]?.lemma" in block

    def test_it_is_fetched_separately_from_the_card(self):
        """The card must be usable before a third party answers, so this
        cannot be part of `/api/lookup`."""
        from eesti import api

        paths = set(api.paths())
        assert "/api/enrich/{word}" in paths and "/api/lookup/{word}" in paths


class TestTheRussianGlossIsRead:
    """The API returns translations twice, and the obvious one is the worse one.

    Top level: `[{"from":"et","to":"en","translations":["book"]}]` — English,
    and only English. Per meaning: `{"rus":[{"words":"книга","weight":1}],
    "eng":[…]}`. The module read the top level, so an app whose stated language
    policy is Russian threw away every Russian gloss the service had.
    """

    PAYLOAD = {
        "estonianWord": "raamat",
        "translations": [{"from": "et", "to": "en", "translations": ["book"]}],
        "searchResult": [{
            "wordClasses": ["noomen"],
            "wordForms": [{"inflectionType": 2, "code": "SgN", "value": "raamat"}],
            "meanings": [{
                "definition": "köidetud lehtede kogum",
                "examples": ["Loen raamatut."],
                "translations": {
                    "rus": [{"words": "книга", "weight": 1},
                            {"words": "книжка", "weight": 0.8}],
                    "fra": [{"words": "livre", "weight": 1}],
                },
            }],
        }],
    }

    def _info(self, tmp_path):
        import json

        (tmp_path / "sonapi").mkdir(parents=True)
        (tmp_path / "sonapi" / "raamat.json").write_text(
            json.dumps(self.PAYLOAD, ensure_ascii=False), encoding="utf-8")
        return sonapi.lookup("raamat", cache_dir=tmp_path)

    def test_russian_comes_through(self, tmp_path):
        assert self._info(tmp_path).russian == ("книга", "книжка")

    def test_codes_are_normalised_to_two_letters(self, tmp_path):
        """One source says `rus`, the other says `ru`. A caller asks once."""
        keys = set(self._info(tmp_path).translations)
        assert keys == {"ru", "fr", "en"}, keys

    def test_the_top_level_still_fills_gaps(self, tmp_path):
        """English is only at the top level for this word; dropping the
        fallback would trade one missing language for another."""
        assert self._info(tmp_path).translations["en"] == ("book",)

    def test_a_word_with_no_translations_is_not_an_error(self, tmp_path):
        import json

        (tmp_path / "sonapi").mkdir(parents=True)
        (tmp_path / "sonapi" / "xx.json").write_text(
            json.dumps({"searchResult": [{"meanings": [{}]}]}), encoding="utf-8")
        info = sonapi.lookup("xx", cache_dir=tmp_path)
        assert info is not None and info.russian == ()


class TestTheDictionaryIsLinkedNotRebuilt:
    """"Don't rebuild what exists" is a plan decision, and Sõnaveeb is the
    named example. A link is how you honour it without a scraper the
    maintainers explicitly asked nobody to write."""

    def test_the_entry_url_is_sonaveebs_own_search_path(self):
        assert sonapi.entry_url("lugema") == (
            "https://sonaveeb.ee/search/unif/dlall/dsall/lugema")

    def test_diacritics_survive(self):
        assert "%C3%B5" in sonapi.entry_url("õppima")

    def test_the_endpoint_hands_the_link_out(self, client, monkeypatch):
        monkeypatch.setattr(sonapi, "lookup", lambda w, **k: sonapi.WordInfo(
            word="lugema", word_classes=(), rection="mida", inflection_type="28",
            definition=None, examples=(),
            translations={"ru": ("читать", "прочитать")}))
        got = client.get("/api/enrich/lugema").json()
        assert got["russian"] == ["читать", "прочитать"]
        assert got["sonaveeb"].endswith("/lugema")


class TestWhatTheAppLinksRatherThanBuilds:
    """Pronunciation scoring is explicitly not being built, on the grounds
    that EKI already publishes free exercises. That is only a decision if the
    learner can reach them; until now the app linked neither them nor the
    situational phrase collections the speaking bank was meant to draw on."""

    @staticmethod
    def _page() -> str:
        from pathlib import Path

        return markup_and_script()

    def test_the_speaking_panel_links_ekis_pronunciation_exercises(self):
        page = self._page()
        panel = page.split('id="tab-speak"')[1].split("</section>")[0]
        assert "sonaveeb.ee/pronunciation-exercises" in panel

    def test_it_links_the_situational_phrase_collections(self):
        page = self._page()
        panel = page.split('id="tab-speak"')[1].split("</section>")[0]
        assert "sonaveeb.ee/learn" in panel

    def test_outbound_links_do_not_hand_over_the_opener(self):
        for chunk in self._page().split("sonaveeb.ee/")[1:]:
            assert 'rel="noopener"' in chunk[:200]

    def test_the_word_card_shows_the_russian_gloss(self):
        page = self._page()
        assert "x.russian" in page and "x.sonaveeb" in page


class TestTheThrottleHoldsUnderConcurrency:
    """A sync FastAPI route runs in a threadpool. Two enrichments arriving
    together read `_last_request` before either writes it, both conclude no
    wait is needed, and fire at once — so the throttle held only while nothing
    was happening, which is the one time nobody needed it."""

    def test_threads_are_spaced_too(self, monkeypatch, tmp_path):
        import threading

        fired: list[float] = []
        lock = threading.Lock()

        def fake_open(url, timeout=None):
            with lock:
                fired.append(time.monotonic())
            raise sonapi.urllib.error.HTTPError(url, 404, "nope", {}, None)

        monkeypatch.setattr(sonapi.urllib.request, "urlopen", fake_open)
        monkeypatch.setattr(sonapi, "MIN_INTERVAL", 0.2)
        monkeypatch.setattr(sonapi, "_last_request", 0.0)

        threads = [threading.Thread(target=sonapi.fetch, args=(w,),
                                    kwargs={"cache_dir": tmp_path})
                   for w in ("aa", "bb", "cc")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        fired.sort()
        assert len(fired) == 3
        gaps = [b - a for a, b in zip(fired, fired[1:])]
        assert all(g >= 0.15 for g in gaps), gaps

