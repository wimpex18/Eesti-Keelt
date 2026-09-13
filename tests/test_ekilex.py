"""Ekilex: the key, the header, the restraint — everything before the parser.

The parser is deliberately not here yet: it is built from a real response
saved by `cli ekilex-probe`, never from a description of one.
"""

from __future__ import annotations

import pytest

from eesti.providers import ekilex


class TestTheKey:
    def test_it_is_a_key_the_app_knows_so_it_can_be_set_in_production(self):
        from eesti.env import KNOWN_KEYS

        assert ekilex.KEY in KNOWN_KEYS

    def test_no_request_is_sent_without_one(self, monkeypatch):
        monkeypatch.delenv(ekilex.KEY, raising=False)
        sent = []
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: sent.append(a))
        with pytest.raises(PermissionError):
            ekilex.get("/word/search/maja")
        assert sent == []

    def test_the_key_travels_in_ekis_header_and_nowhere_else(self, monkeypatch):
        monkeypatch.setenv(ekilex.KEY, "test-key-not-real")
        monkeypatch.setattr(ekilex, "MIN_INTERVAL", 0)
        seen = {}

        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b"[]"

        def fake(request, timeout):
            seen["url"], seen["headers"] = request.full_url, dict(request.header_items())
            return Response()

        monkeypatch.setattr("urllib.request.urlopen", fake)
        assert ekilex.get("/word/search/maja") == []
        assert seen["headers"].get("Ekilex-api-key") == "test-key-not-real"
        assert "test-key-not-real" not in seen["url"]


class TestTheProbe:
    def test_without_a_key_it_says_where_to_put_one(self, monkeypatch, capsys, tmp_path):
        from eesti import env
        from eesti.cli import main

        monkeypatch.delenv(ekilex.KEY, raising=False)
        monkeypatch.setattr(env, "ENV_FILE", tmp_path / "absent.env")
        assert main(["ekilex-probe", "maja"]) == 2
        assert ".env" in capsys.readouterr().out

    def test_shape_names_keys_and_never_values(self):
        lines = ekilex.shape({"lexemes": [{"meaning": {"definitions": [{"value": "secret text"}]}}]})
        assert any("definitions" in l for l in lines)
        assert not any("secret text" in l for l in lines)
