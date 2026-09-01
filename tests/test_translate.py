"""Sentence translation — the endpoint that was configured and never called.

`TARTUNLP_TRANSLATE` sat in `config.py` from the first week with no caller
anywhere in the codebase. That is the same defect as a measurement with no
writer, and it cost more than a dead constant: it is a free, keyless,
Estonian-trained service sitting unused beside a grammar endpoint on the same
host that has failed every probe since the first research round.

The tests here never touch the network. What they pin is the shape and the
posture — that it degrades to None rather than raising, and that nothing calls
it automatically, because a reader handed Russian reads the Russian.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from eesti.providers import translate as t

from pagesrc import markup_and_script


class FakeResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestItAnswersInTheShapeTheApiUses:
    def test_a_bare_string_result(self, monkeypatch):
        monkeypatch.setattr(t.urllib.request, "urlopen",
                            lambda *a, **k: FakeResponse({"result": "Я читал книгу."}))
        got = t.translate("Ma lugesin raamatut.")
        assert got.text == "Я читал книгу." and got.target == "rus"
        assert got.engine == "tartunlp"

    def test_a_list_result_is_joined(self, monkeypatch):
        """The endpoint returns a list for a batch and a string for one input."""
        monkeypatch.setattr(t.urllib.request, "urlopen",
                            lambda *a, **k: FakeResponse({"result": ["Раз.", "Два."]}))
        assert t.translate("Üks. Kaks.").text == "Раз. Два."

    def test_the_source_is_kept_alongside(self, monkeypatch):
        monkeypatch.setattr(t.urllib.request, "urlopen",
                            lambda *a, **k: FakeResponse({"result": "Кот."}))
        assert t.translate("  Kass.  ").source == "Kass."


class TestItIsACrutchAndFailsLikeOne:
    @pytest.mark.parametrize("boom", [
        urllib.error.URLError("down"),
        TimeoutError("slow"),
        OSError("refused"),
    ])
    def test_a_dead_service_returns_none_rather_than_raising(self, monkeypatch, boom):
        """A crutch that raises is worse than one quietly absent for a minute."""
        def explode(*a, **k):
            raise boom

        monkeypatch.setattr(t.urllib.request, "urlopen", explode)
        assert t.translate("Tere.") is None

    def test_malformed_json_is_not_an_exception(self, monkeypatch):
        class Broken:
            def read(self): return b"not json"
            def __enter__(self): return self
            def __exit__(self, *a): return False

        monkeypatch.setattr(t.urllib.request, "urlopen", lambda *a, **k: Broken())
        assert t.translate("Tere.") is None

    def test_an_empty_result_is_none(self, monkeypatch):
        monkeypatch.setattr(t.urllib.request, "urlopen",
                            lambda *a, **k: FakeResponse({"result": "   "}))
        assert t.translate("Tere.") is None

    @pytest.mark.parametrize("text", ["", "   ", None])
    def test_nothing_in_nothing_out(self, text):
        assert t.translate(text) is None

    def test_an_unsupported_target_is_refused_before_the_request(self, monkeypatch):
        def explode(*a, **k):
            raise AssertionError("went to the network for a language it cannot do")

        monkeypatch.setattr(t.urllib.request, "urlopen", explode)
        assert t.translate("Tere.", target="klingon") is None

    def test_a_long_text_is_truncated_not_refused(self, monkeypatch):
        sent = {}

        def capture(request, *a, **k):
            sent["len"] = len(json.loads(request.data)["text"])
            return FakeResponse({"result": "ok"})

        monkeypatch.setattr(t.urllib.request, "urlopen", capture)
        t.translate("Ma " * 2000)
        assert sent["len"] == t.MAX_CHARS


class TestTheEndpointAndItsPosture:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        return TestClient(app_module.app)

    def test_a_dead_service_is_not_an_error_page(self, client, monkeypatch):
        monkeypatch.setattr(t, "translate", lambda *a, **k: None)
        got = client.post("/api/translate", json={"text": "Tere."})
        assert got.status_code == 200 and got.json()["ok"] is False
        assert got.json()["detail"]

    def test_it_answers_when_the_service_does(self, client, monkeypatch):
        monkeypatch.setattr(
            t, "translate",
            lambda *a, **k: t.Translation("Tere.", "Привет.", "rus"))
        got = client.post("/api/translate", json={"text": "Tere."}).json()
        assert got["ok"] is True and got["text"] == "Привет."

    def test_nothing_renders_a_translation_on_its_own(self):
        """Offered, never shown. A reader handed Russian reads the Russian, and
        this app's reading design rests on working at the edge of what is
        understood rather than past it."""
        from pathlib import Path

        page = markup_and_script()
        assert '"/api/translate"' in page
        # The only call site is behind a button the learner presses.
        before = page.split('"/api/translate"', 1)[0]
        assert "#xlBtn" in before, "translation is not behind an explicit action"

    def test_the_route_has_a_caller(self):
        """The bug being fixed: `TARTUNLP_TRANSLATE` was configured with none."""
        from pathlib import Path

        page = markup_and_script()
        assert "/api/translate" in page


class TestBackTranslationInTheWritingCheck:
    """A grammar chain says whether the Estonian is well formed. It cannot say
    whether it means what was intended, and that second failure is the more
    common and the far more invisible one for a learner.

    `Ma käisin arstiga` is perfect Estonian and means you went *with* a doctor.
    Nothing in the chain flags it; reading it back in Russian does.
    """

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        return TestClient(app_module.app)

    def test_the_check_carries_what_the_text_says(self, client, monkeypatch):
        monkeypatch.setattr(
            t, "translate",
            lambda *a, **k: t.Translation("Ma käisin arstiga.",
                                          "Я ходил с врачом.", "rus"))
        got = client.post("/api/check", json={"text": "Ma käisin arstiga."}).json()
        assert got["back_translation"] == "Я ходил с врачом."

    def test_a_dead_translator_does_not_break_the_check(self, client, monkeypatch):
        """The grammar check is the feature; this is an addition to it."""
        monkeypatch.setattr(t, "translate", lambda *a, **k: None)
        got = client.post("/api/check", json={"text": "Ma käisin arstiga."})
        assert got.status_code == 200
        assert got.json()["back_translation"] is None
        assert "corrections" in got.json()

    def test_the_page_renders_it(self):
        from pathlib import Path

        page = markup_and_script()
        assert "res.back_translation" in page
