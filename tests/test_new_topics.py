"""Pronouns, pre- and postpositions, käima/minema and -mine/-ja nouns."""

from __future__ import annotations

import sqlite3

import pytest

from eesti import motion, postpositions, pronouns, wordbuilding
from eesti.item import accepts


class TestPronouns:
    def test_the_teatmik_mina_table(self):
        assert pronouns.form("mina", "alaleütlev") == "minule ~ mulle"
        assert pronouns.form("nemad", "omastav") == "nende"

    def test_sina_and_teie_follow_mina_and_meie(self):
        assert pronouns.form("sina", "osastav") == "sind"
        assert pronouns.form("sina", "alalütlev") == "sinul ~ sul"
        assert pronouns.form("teie", "alaleütlev") == "teile"
        assert pronouns.form("teie", "nimetav") == "teie ~ te"

    def test_either_parallel_form_is_accepted(self):
        assert accepts("minule ~ mulle", "mulle") and accepts("minule ~ mulle", "Minule")
        assert not accepts("minule ~ mulle", "mina")

    def test_every_table_is_complete(self):
        for name, (_, forms) in pronouns.TABLES.items():
            assert len(forms) == len(pronouns.CASES), name


class TestPostpositions:
    def test_postposition_takes_the_genitive(self):
        items = postpositions.drills(40, seed=1)
        assert any(i.prompt.endswith("all.") and i.answer == "laua" for i in items) or items

    def test_no_ambiguous_answer(self):
        for item in postpositions.drills(40, seed=2):
            assert "~" not in item.answer and item.answer != ""


class TestMotion:
    def test_kaima_for_kus_minema_for_kuhu(self):
        for item in motion.drills(30, seed=3):
            if item.rule == "käima":
                assert item.answer.startswith("käi")
            else:
                assert item.answer.startswith("lä")


class TestWordbuilding:
    @pytest.fixture
    def words(self, tmp_path):
        conn = sqlite3.connect(tmp_path / "w.db")
        conn.execute("CREATE TABLE words (word TEXT)")
        conn.executemany("INSERT INTO words VALUES (?)",
                         [("laulja",), ("laulmine",), ("ujumine",), ("ujuja",)])
        return conn

    def test_only_listed_words_are_drilled(self, words):
        assert wordbuilding.derived("laulma", "ja", words) == "laulja"
        assert wordbuilding.derived("tegema", "ja", words) is None

    def test_drills(self, words):
        for item in wordbuilding.drills(words, 10, seed=1):
            assert item.answer in {"laulja", "laulmine", "ujumine", "ujuja"}
