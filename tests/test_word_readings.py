"""Which reading of a word the card names.

Two rules:

- **The form index only holds forms Vabamorf reads back.** `synthesize` answers
  every request, so an adverb got fourteen "plural cases" (`kus` as *mitmuse
  ilmaütlev*) and a postposition a plural (`aadressilideta`). The export keeps a
  row only when analysing the form finds the same lemma and tag.
- **A sentence chooses.** With the sentence a word was met in, Vabamorf's
  disambiguator marks the reading it uses: `teed` is tea in *Ma joon teed* and
  roads in *Need teed viivad linna*; `mulle` in *Anna mulle raamat* is `mina`,
  so "Kordamisse" does not queue a card for `mull` (a bubble).
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import export, lookup

LEMMAS = [("kus", "A1", 30, "adv"), ("tee", "A1", 200, "s"),
          ("tegema", "A1", 50, "v"), ("mina", "A1", 5, "pron"),
          ("mull", None, 9000, "s"), ("aadressil", None, 9000, "postp")]


@pytest.fixture
def edge(tmp_path, monkeypatch):
    src = sqlite3.connect(tmp_path / "words.db")
    src.execute("CREATE TABLE words (word TEXT, proficiency TEXT, freq_rank INT, pos TEXT)")
    src.executemany("INSERT INTO words VALUES (?,?,?,?)", LEMMAS)
    path = tmp_path / "edge.db"
    export.export(src, path)
    monkeypatch.setattr(lookup, "EDGE_DB", path)
    return sqlite3.connect(path)


class TestTheIndexHoldsOnlyRealForms:
    def test_an_adverb_has_no_invented_cases(self, edge):
        assert edge.execute("SELECT tag FROM forms WHERE lemma = 'kus'").fetchall() == [("",)]

    def test_a_postposition_has_no_invented_plural(self, edge):
        assert not edge.execute(
            "SELECT 1 FROM forms WHERE form = 'aadressilideta'").fetchone()

    def test_real_forms_stay(self, edge):
        tags = {r[0] for r in edge.execute(
            "SELECT tag FROM forms WHERE form = 'teed'")}
        assert {"sg p", "pl n", "d"} <= tags

    def test_the_card_names_the_part_of_speech_instead(self, edge):
        (kus,) = lookup.lookup("kus")["analyses"]
        assert kus["tags"] == []
        assert (kus["pos_name"], kus["pos_ru"]) == ("määrsõna", "наречие")


class TestTheSentenceChooses:
    @pytest.mark.parametrize("sentence, lemma, tag", [
        ("Ma joon hommikul teed.", "tee", "sg p"),
        ("Need teed viivad linna.", "tee", "pl n"),
        ("Anna mulle raamat.", "mina", "sg all"),
    ])
    def test_the_reading_in_the_sentence_comes_first(self, edge, sentence, lemma, tag):
        word = "teed" if "teed" in sentence else "mulle"
        got = lookup.lookup(word, sentence)
        assert got["in_context"] is True
        first = got["analyses"][0]
        assert first["lemma"] == lemma and first["in_context"] is True
        assert first["tags"][0] == {**first["tags"][0], "tag": tag, "in_context": True}

    def test_without_a_sentence_nothing_is_marked(self, edge):
        got = lookup.lookup("teed")
        assert got["in_context"] is False
        assert not any(a.get("in_context") for a in got["analyses"])

    def test_the_api_takes_the_sentence(self, client, edge):
        got = client.get("/api/lookup/teed", params={"sentence": "Need teed viivad linna."}).json()
        assert got["analyses"][0]["tags"][0]["tag"] == "pl n"

    def test_kordamisse_queues_the_word_the_sentence_uses(self, edge, tmp_path, monkeypatch):
        from eesti import mining, review

        chosen = {}
        monkeypatch.setattr(mining, "_meaning_card",
                            lambda conn, lemma, context, analysis=None:
                            chosen.setdefault("lemma", lemma) and mining.MineResult(False, ""))
        mining.from_reading(review.connect(tmp_path / "review.db"), "mulle",
                            context="Anna mulle raamat.")
        assert chosen["lemma"] == "mina"
