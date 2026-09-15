"""Ekilex: the key and header, the probe, parsing real (trimmed) responses, and the
word card's use of them.
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


def _fixture(word):
    import json
    from pathlib import Path

    return json.loads((Path(__file__).parent / "fixtures" / "ekilex" / f"{word}.json")
                      .read_text(encoding="utf-8"))["details"]


class TestReadingRealResponses:
    """Trimmed from real `cli ekilex-probe` answers."""

    def test_russian_is_the_senses_own_words_not_related_meanings(self):
        """`MEANING_REL` entries counted, `kohus` ("duty") read угнетение, иго."""
        got = ekilex.parse(_fixture("kohus"))
        assert got.russian == ("долг", "обязанность")

    def test_the_main_sense_leads(self):
        assert ekilex.parse(_fixture("poiss")).russian[:3] == ("мальчик", "мальчишка", "мальчуган")

    def test_learner_and_native_definitions_are_kept_apart(self):
        got = ekilex.parse(_fixture("maja"))
        assert got.learner_definition == "hoone, kus inimesed elavad või töötavad"
        assert got.definition.startswith("hoone inimestele elamiseks")

    def test_rection_type_and_level(self):
        got = ekilex.parse(_fixture("lugema"))
        assert got.governs == ("mida", "kust", "kellele")
        assert (got.inflection_type, got.level) == ("28", "A1")

    def test_a_secondary_paradigm_is_not_the_type(self):
        assert ekilex.parse(_fixture("poiss")).inflection_type == "23e"

    def test_an_archaic_sense_contributes_nothing(self):
        assert "право" not in ekilex.parse(_fixture("kohus")).russian


class TestTheStoreAndTheCard:
    def test_the_live_answer_is_stored_with_its_source_and_learner_wording(self, tmp_path, monkeypatch):
        from eesti import gloss

        monkeypatch.setenv(ekilex.KEY, "test-key-not-real")
        monkeypatch.setattr(ekilex, "lookup", lambda w: ekilex.parse(_fixture("maja")))
        store = gloss.connect(tmp_path / "vocab.db", seed_glosses=False)
        got = gloss.remember(store, "maja")
        assert (got.source, got.level) == ("ekilex", "A1")
        assert got.learner_definition == "hoone, kus inimesed elavad või töötavad"

    def test_without_a_key_the_mirror_is_asked(self, tmp_path, monkeypatch):
        from eesti import gloss
        from eesti.providers import sonapi

        asked = []
        monkeypatch.setattr(sonapi, "lookup", lambda w: asked.append(w))
        monkeypatch.setattr(ekilex, "lookup", lambda w: pytest.fail("no key, no Ekilex"))
        gloss.remember(gloss.connect(tmp_path / "vocab.db", seed_glosses=False), "maja")
        assert asked == ["maja"]

    def test_the_card_leads_with_ekilexs_learner_definition_and_credits_it(self, client, monkeypatch):

        monkeypatch.setenv(ekilex.KEY, "test-key-not-real")
        monkeypatch.setattr(ekilex, "lookup", lambda w: ekilex.parse(_fixture("lugema")))
        got = client.get("/api/enrich/lugema").json()
        assert got["definition"] == "mingit teksti vaatama ja sellest aru saama"
        assert got["definition_source"] == "ekilex"
        assert got["governs"] == ["mida", "kust", "kellele"]
        assert got["governs_source"] == "ekilex"
        assert got["full_definition_source"] == "ekilex"

    def test_an_old_store_gains_the_columns(self, tmp_path):
        import sqlite3

        from eesti import gloss

        path = tmp_path / "old.db"
        raw = sqlite3.connect(path)
        raw.execute("CREATE TABLE word_gloss (lemma TEXT PRIMARY KEY, russian TEXT NOT NULL DEFAULT '',"
                    " definition TEXT, rection TEXT, inflection_type TEXT,"
                    " found INTEGER NOT NULL DEFAULT 1, fetched TEXT NOT NULL)")
        raw.commit(); raw.close()
        conn = gloss.connect(path, seed_glosses=False)
        assert {"learner_definition", "level", "source"} <= {r[1] for r in conn.execute("PRAGMA table_info(word_gloss)")}

    def test_the_card_never_pairs_one_senses_definition_with_anothers_russian(self, client, monkeypatch):
        """`kohus` is seeded as "суд"; Ekilex's first homonym is "duty"."""
        monkeypatch.setenv(ekilex.KEY, "test-key-not-real")
        monkeypatch.setattr(ekilex, "lookup", lambda w: ekilex.parse(_fixture("kohus")))
        got = client.get("/api/enrich/kohus").json()
        assert got["russian"] == ["долг", "обязанность"] and got["russian_source"] == "ekilex"
