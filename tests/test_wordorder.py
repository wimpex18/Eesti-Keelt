"""Word order: the second-biggest error class, and why its items are attested.

Of the 51 467 errors annotated in EVKK, `word-order` takes 11.4 % of all marks
and 19.3 % of those the nine tags cover — second only to vocabulary — and it
was one of three tags nothing in this app could practise.

The interesting tests here are the refusals. Estonian word order is flexible,
so a generated distractor is sometimes correct Estonian, and a drill that marks
correct Estonian wrong teaches the opposite of the rule.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from eesti import wordorder


@pytest.fixture
def pairs():
    """Attested (learner wrote, native corrected) pairs, hand-picked from
    `grammar_et` so the test does not need the download."""
    return [
        # V2: the verb pulled into second position after a fronted adverbial.
        ("Oktoobris vihmased päevad vahelduvad kirgastega.",
         "Oktoobris vahelduvad vihmased päevad kirgastega."),
        # A native's re-ordering with no rule behind it.
        ("Praegu on talv ja minu esimene semester varsti lõpeb.",
         "Praegu on talv ja minu esimene semester lõpeb varsti."),
        # Not a re-ordering: words were changed, so it is a different error.
        ("Kellena küll saaksin?", "Kelleks küll saaksin?"),
    ]


class TestOnlyReorderingsAreKept:
    def test_a_changed_word_is_not_a_word_order_error(self, pairs):
        assert not wordorder.is_reordering(*pairs[2])

    def test_same_words_in_a_different_sequence_is(self, pairs):
        assert wordorder.is_reordering(*pairs[0])

    def test_an_identical_pair_is_not_an_error_at_all(self):
        assert not wordorder.is_reordering("Ma elan siin.", "Ma elan siin.")

    def test_the_filter_survives_punctuation_and_case(self):
        assert not wordorder.is_reordering("Ma elan siin.", "ma elan siin")

    def test_items_are_built_only_from_the_reorderings(self, pairs):
        items = wordorder.from_pairs(pairs)
        assert len(items) == 2


class TestTheRuleIsOnlyClaimedWhereItCanBeRead:
    """Two rules are claimed because two can be read off morphology. Calling
    everything else `other` is what keeps the explanations honest."""

    def test_v2_is_recognised(self):
        rule, moved = wordorder.classify(
            "Oktoobris vihmased päevad vahelduvad.",
            "Oktoobris vahelduvad vihmased päevad.")
        assert rule == "v2" and moved == "vahelduvad"

    def test_a_split_negation_is_recognised(self):
        rule, _ = wordorder.classify("Ma ei kunagi tea seda.",
                                     "Ma ei tea kunagi seda.")
        assert rule == "negation"

    def test_a_stylistic_move_is_not_dressed_up_as_a_rule(self):
        rule, _ = wordorder.classify(
            "Praegu on talv ja minu esimene semester varsti lõpeb.",
            "Praegu on talv ja minu esimene semester lõpeb varsti.")
        assert rule == "other"

    def test_the_v2_explanation_does_not_overstate_it(self):
        """EKK (SÜ 90) says the finite verb is *usually* second and calls
        inversion a means of emphasis. Measuring 1 000 native-corrected
        sentences gave 75.4 % inversion in this shape. An absolute rule here
        would have the learner "correcting" good Estonian."""
        why = wordorder.WHY["v2"]
        assert "обычно" in why
        assert "всегда" not in why

    def test_the_unruled_explanation_claims_only_what_it_can(self):
        why = wordorder.WHY["other"]
        assert "носитель" in why          # a native wrote it
        assert "ошибк" in why             # and says this is not about an error

    def test_every_explanation_is_in_russian(self):
        for why in wordorder.WHY.values():
            assert any("Ѐ" <= ch <= "ӿ" for ch in why)


class TestGenerationIsRefused:
    """The measurement that ruled it out, kept as a test so the reasoning is
    not quietly dropped by someone adding a corpus generator later."""

    def test_the_module_has_no_corpus_generator(self):
        assert not hasattr(wordorder, "from_corpus")

    def test_the_docstring_records_the_measurement(self):
        doc = wordorder.__doc__ or ""
        assert "75.4" in doc, "the number that ruled generation out"
        assert "syntax" in doc and "morphology" in doc


class TestThePracticeShape:
    @pytest.fixture
    def content(self, tmp_path, pairs, monkeypatch):
        from eesti import config

        path = tmp_path / "content.db"
        monkeypatch.setattr(config, "CONTENT_DB", str(path))
        raw = tmp_path / "grammar_et.json"
        raw.write_text(json.dumps(
            [{"original": w, "correct": r} for w, r in pairs]), encoding="utf-8")
        from eesti.sources import connect

        conn = connect(path)
        assert wordorder.ingest(conn, raw) == 2
        return conn

    def test_items_reach_the_content_store(self, content):
        got = wordorder.items(content, limit=10)
        assert len(got) == 2

    def test_the_rule_bearing_item_comes_first(self, content):
        """A session should open on the one that teaches something."""
        assert wordorder.generate(count=2, seed=1, content=content)[0].rule == "v2"

    def test_it_offers_exactly_two_whole_sentences(self, content):
        for item in wordorder.generate(count=2, seed=1, content=content):
            assert len(item.choices) == 2
            assert set(item.choices) == {item.answer, item.distractor}

    def test_the_right_answer_is_not_always_in_the_same_place(self, content):
        firsts = {wordorder.generate(count=1, seed=s, content=content)[0].choices[0]
                  for s in range(12)}
        assert len(firsts) > 1, "a fixed position is learnable without reading"

    def test_grading_is_the_same_comparison_every_item_uses(self, content):
        """That is what lets this reach mastery and the review queue through
        the existing path rather than needing a loop of its own."""
        item = wordorder.generate(count=1, seed=1, content=content)[0]
        assert item.check(item.answer)
        assert not item.check(item.distractor)

    def test_the_rule_ships_with_the_exercise(self, content):
        item = wordorder.generate(count=1, seed=1, content=content)[0]
        assert item.reference["ekk_section"] == "SÜ 90"

    def test_no_corpus_is_an_empty_list_not_a_crash(self):
        assert wordorder.generate(count=3, content=None, path=None) == []

    def test_the_topic_now_has_a_generator(self):
        """`sonajark` was a dead end in the path: reachable and unpractisable."""
        from eesti.curriculum import by_id

        assert by_id("sonajark").generator == "wordorder"

    def test_the_practice_loop_serves_it(self, content):
        from eesti.practice import items_for

        got = items_for("sonajark", count=2, seed=1)
        assert got and all(i.choices for i in got)


class TestTheLicenceDecisionIsRecorded:
    def test_the_source_is_registered_as_ungranted(self):
        from eesti.sources import REGISTRY

        src = next(s for s in REGISTRY if s.id == wordorder.SOURCE_ID)
        assert src.redistributable is False
        assert "no licence" in src.licence.lower()
