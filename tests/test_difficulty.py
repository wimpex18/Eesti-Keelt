"""Two questions about a text, kept apart.

**Band** — difficulty relative to other texts from the same source ("where do I
start"). **Comprehensibility** — the share of lemmas this learner knows ("what
next"). Neither is a CEFR level, and `band` never goes in the `level` column.
"""

from __future__ import annotations


from eesti.difficulty import (BANDS, INDEPENDENT, INSTRUCTIONAL, CAVEAT,
                              comprehensible, known_lemmas, rank)


class TestBands:
    def test_a_corpus_is_split_into_thirds(self):
        texts = {str(i): f"Ma olen kodus number {i}." for i in range(9)}
        bands = rank(texts)
        assert set(bands.values()) <= set(BANDS)
        assert len(bands) == 9

    def test_too_few_texts_to_rank_is_not_ranked(self):
        """Thirds of two items is a distinction the data cannot support, and
        inventing one puts a text in `kergem` for no reason a reader can use."""
        assert set(rank({"a": "Üks.", "b": "Kaks."}).values()) == {"keskmine"}

    def test_an_empty_corpus_is_empty(self):
        assert rank({}) == {}

    def test_the_caveat_says_it_is_not_a_level(self):
        """In Russian, because it is what stops a band being read as CEFR."""
        assert "CEFR" in CAVEAT
        assert any("Ѐ" <= ch <= "ӿ" for ch in CAVEAT)


class TestComprehensibility:
    def test_a_text_of_known_words_is_independent(self):
        """Coverage uses the same lemmatiser for the known set, so the test checks the
        arithmetic, not dictionary spellings.
        """
        from eesti.lookup import lemmas_in

        text = "Ma olen kodus."
        got = comprehensible(text, set(lemmas_in(text)))
        assert got["coverage"] >= INDEPENDENT
        assert got["readability"] == "iseseisev"

    def test_partial_knowledge_lands_between_the_thresholds(self):
        from eesti.lookup import lemmas_in

        text = "Ma olen kodus ja loen raamatut."
        lemmas = lemmas_in(text)
        got = comprehensible(text, set(lemmas[: len(lemmas) // 2]))
        assert 0.0 < got["coverage"] < INDEPENDENT

    def test_a_text_of_unknown_words_is_hard(self):
        got = comprehensible("Rahvastikuregistri andmetel vähenes iive.", set())
        assert got["coverage"] == 0.0
        assert got["readability"] == "raske"

    def test_the_middle_band_is_where_a_text_teaches(self):
        assert INSTRUCTIONAL < INDEPENDENT
        assert 0.85 <= INSTRUCTIONAL <= 0.95

    def test_an_empty_text_claims_nothing(self):
        """Official material has an empty body — it is a pointer, not a text.
        Scoring it 0 % would rank every exam task as unreadable."""
        got = comprehensible("", {"ma"})
        assert got["readability"] is None
        assert got["total"] == 0

    def test_no_vocabulary_recorded_is_not_an_error(self):
        assert known_lemmas(None) == set()

    def test_it_is_vocabulary_coverage_not_comprehension(self):
        """Knowing every word in a sentence does not guarantee understanding
        it. The field is named for what it measures."""
        got = comprehensible("Ma olen kodus.", {"ma", "olema", "kodu"})
        assert "coverage" in got
        assert "comprehension" not in got
        assert "score" not in got


class TestTheTwoScalesStayApart:
    def test_official_material_carries_cefr_and_no_band(self):
        from eesti.harvest.harno import Material, to_items

        item = to_items([Material(url="u", level="B1", skill="lugemine",
                                  title="B1 Lu1", kind="ulesanne",
                                  fmt="pdf")])[0]
        assert item.level == "B1"
        assert item.band is None

    def test_harvested_prose_carries_a_band_and_no_cefr(self):
        from eesti.harvest.lihtsad import Issue, to_items

        issues = [Issue(url=f"u{i}", title=f"T{i}",
                        body=f"Ma olen kodus {i}. " * 20, published=None)
                  for i in range(6)]
        items = to_items(issues)
        assert all(i.level is None for i in items)
        assert all(i.band in BANDS for i in items)
