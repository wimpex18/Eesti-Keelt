"""Rection in free writing: EVKK's `&err-gov`.

A lookup against EKK SÜ 64's attested confusions, flagged only when: the headword
is an EKK contrast, a word in its own clause stands in the starred wrong case,
and nothing in that clause stands in the correct case.
"""

from __future__ import annotations

import pytest

from eesti import rection
from eesti.providers import grammar

#: EKK's real contrasts, as `cli rections` stores them. Written out rather than
#: loaded so these run without a word list — the same reason the EKI and PSV
#: fixtures exist.
RULES = [
    rection.Rection("põhinema", "millel", "millele", "sg ad", "sg all"),
    rection.Rection("kohanema", "millega", "millele", "sg kom", "sg all"),
    rection.Rection("sarnanema", "millega", "millele", "sg kom", "sg all"),
    rection.Rection("nautima", "mida", "millest", "sg p", "sg el"),
]


class TestItCatchesTheAttestedConfusion:
    @pytest.mark.parametrize(("text", "wrong", "correct"), [
        ("See süsteem põhineb faktidel.", None, None),
        ("See süsteem põhineb faktidele.", "faktidele", "faktidel"),
        ("See raamat sarnaneb teisele raamatule.", "raamatule", "raamatuga"),
    ])
    def test_it_names_the_case_that_belongs(self, text, wrong, correct):
        found = rection.errors(text, RULES)
        if wrong is None:
            assert found == []
        else:
            assert [(m.wrong, m.correct) for m in found] == [(wrong, correct)]

    def test_the_number_the_learner_used_is_kept(self):
        """Plural complements are checked too: the case is compared, not the number."""
        assert rection.errors("See põhineb faktidele.", RULES)[0].correct == "faktidel"

    def test_an_agreeing_modifier_is_part_of_the_complement_not_a_rival(self):
        """`uuele olukorrale` is one noun phrase. Counting the adjective as a
        second candidate made every modified phrase look ambiguous, and the
        first version of this check fired on nothing at all."""
        found = rection.errors("Ma pean kohanema uuele olukorrale.", RULES)
        assert [(m.wrong, m.correct) for m in found] == [
            ("olukorrale", "olukorraga")]

    def test_the_span_points_at_the_complement(self):
        text = "Ma pean kohanema uuele olukorrale."
        m = rection.errors(text, RULES)[0]
        assert text[m.start:m.end] == "olukorrale"


class TestItDoesNotInventErrors:
    def test_the_right_case_present_means_the_learner_got_it_right(self):
        """If the correct complement is there, a word in the starred case
        belongs to something else."""
        assert rection.errors("Ma pean kohanema uue olukorraga.", RULES) == []

    def test_a_clause_boundary_stops_the_search(self):
        """Estonian marks subordinate clauses with a comma reliably. Without
        this, `sõbrale` — allative, `põhinema`'s starred case — is flagged from
        the other side of a comma while the real complement sits by the verb."""
        assert rection.errors(
            "Ma kirjutasin sõbrale, et süsteem põhineb loogikal.", RULES) == []

    def test_two_rival_noun_phrases_are_left_alone(self):
        """More than one noun in the starred case and there is no telling which
        the verb governs. That is the syntax this project does not have."""
        assert rection.errors(
            "Ma pean kohanema olukorrale majale.", RULES) == []

    def test_a_verb_not_on_ekks_list_is_never_judged(self):
        """Nothing is claimed about rections EKK does not record as confused —
        that would be valency, and this is a lookup."""
        assert rection.errors("Ma kirjutasin sõbrale kirja.", RULES) == []

    def test_no_rules_means_no_claims(self):
        assert rection.errors("See süsteem põhineb faktidele.", []) == []


class TestItReachesTheLearner:
    def test_it_is_merged_into_whatever_the_chain_answered(self, monkeypatch):
        monkeypatch.setattr(grammar, "rection", lambda text: [
            grammar.Correction("olukorrale", "olukorraga", "…", "rektsioon")])

        class _Answering:
            name = "pretend-llm"

            def available(self):
                return True

            def check(self, text):
                return grammar.GrammarResult(self.name, [])

        answer = grammar.check("Ma pean kohanema uuele olukorrale.",
                               providers=[_Answering()])
        assert [c.tag for c in answer.corrections] == ["rektsioon"]

    def test_it_is_tagged_so_the_error_log_can_group_it(self):
        from eesti.config import TAGS

        assert "rektsioon" in TAGS

    def test_it_explains_in_russian_and_keeps_ekks_own_frame_words(self):
        why = grammar.RECTION_WHY.format(
            headword="kohanema", correct="olukorraga", correct_frame="millega",
            wrong="olukorrale", wrong_frame="millele")
        assert "millega" in why and "millele" in why
        assert "SÜ 64" in why, "the learner can check the handbook"
        assert any("Ѐ" <= ch <= "ӿ" for ch in why), "must be Russian"

    def test_it_degrades_to_nothing_without_a_word_list(self, monkeypatch):
        """The contrasts live in the word list, and a fresh checkout has none.
        An enrichment is never worth an error."""
        monkeypatch.setattr("eesti.wordlist.available", lambda *a, **k: False)
        assert grammar.rection("See süsteem põhineb faktidele.") == []
