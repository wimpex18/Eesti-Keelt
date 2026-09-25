"""Telling the time and dates: the hour counts forward, the date is an ordinal
in alalütlev, and every answer comes from Vabamorf."""

from __future__ import annotations

import pytest

from eesti.timedate import date_drills, ordinal, ordinal_form, time_drills


class TestOrdinals:
    @pytest.mark.parametrize("n,lemma", [
        (1, "esimene"), (10, "kümnes"), (11, "üheteistkümnes"),
        (18, "kaheksateistkümnes"), (20, "kahekümnes"), (21, "kahekümne esimene"),
        (30, "kolmekümnes"), (31, "kolmekümne esimene"),
    ])
    def test_lemma(self, n, lemma):
        assert ordinal(n) == lemma

    def test_only_the_last_word_declines(self):
        assert ordinal_form(21, "sg ad") == "kahekümne esimesel"
        assert ordinal_form(30, "sg tr") == "kolmekümnendaks"


class TestTime:
    def test_a_fraction_counts_towards_the_next_hour(self):
        for item in time_drills(40, seed=3):
            if " pool " in item.prompt or "veerand" in item.prompt:
                hour = int(item.answer_ru[0].split(".")[0])
                assert item.answer != item.distractor
                assert item.distractor.startswith(("üks", "kaks", "kolm", "neli", "viis",
                                                   "kuus", "seitse", "kaheksa", "üheksa",
                                                   "kümme"))
                assert hour in range(1, 13)

    def test_nine_thirty_is_pool_kumme(self):
        items = [i for i in time_drills(200, seed=1) if i.answer_ru == ("9.30",)]
        assert items and all(i.answer == "kümme" for i in items)

    def test_every_item_has_a_cue_and_no_lemma(self):
        for item in time_drills(20, seed=5) + date_drills(20, seed=5):
            assert item.answer_ru and not item.lemma

    def test_answers_grade(self):
        for item in time_drills(10, seed=2) + date_drills(10, seed=2):
            assert item.check(item.answer) and not item.check(item.distractor or "x")
