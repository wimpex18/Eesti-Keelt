"""The word card names every tag it can show, in Estonian and with a Russian gloss."""

from __future__ import annotations

from eesti import cloze
from eesti.lookup import TAG_NAMES, TAG_RU


class TestEveryTagIsNamed:
    def test_every_named_tag_has_a_russian_gloss(self):
        assert set(TAG_NAMES) == set(TAG_RU)

    def test_both_numbers_of_every_case_are_named(self):
        cases = {t.split()[1] for t in TAG_NAMES if t.startswith("sg ")}
        assert {f"pl {c}" for c in cases} <= set(TAG_NAMES)

    def test_case_glosses_match_the_drills(self):
        """The card and the drill explanation call a case the same thing."""
        for tag, (_, ru) in cloze.CASES.items():
            if tag.startswith("sg "):
                assert TAG_RU[tag] == f"ед. ч., {ru}", tag


class TestRussianCounts:
    def test_readiness_counts_agree_with_the_number(self):
        from eesti.readiness import _count

        forms = ("текст", "текста", "текстов")
        assert [_count(n, *forms) for n in (0, 1, 2, 5, 11, 21, 22, 112)] == [
            "0 текстов", "1 текст", "2 текста", "5 текстов", "11 текстов",
            "21 текст", "22 текста", "112 текстов"]
