"""Subject–verb agreement: decided from morphology and corrected with a
Vabamorf-synthesised form.

Rules and exceptions follow GiellaLT's Estonian Constraint Grammar
(`giellalt/lang-est-x-utee`, `&err-agr`); the exceptions keep correct Estonian
from being flagged.
"""

from __future__ import annotations

import pytest

from eesti import morph
from eesti.providers import grammar


class TestItCatchesRealDisagreement:
    @pytest.mark.parametrize(("text", "correct"), [
        ("Ma elab Tallinnas.", "elan"),
        ("Me elab siin.", "elame"),
        ("Nad elab siin.", "elavad"),
        ("Ta elavad siin.", "elab"),
        ("Sa elame kodus.", "elad"),
    ])
    def test_it_names_the_form_that_belongs_there(self, text, correct):
        found = morph.agreement_errors(text)
        assert len(found) == 1, text
        assert found[0].correct == correct

    def test_the_span_points_at_the_verb_not_the_pronoun(self):
        """The pronoun is right; the verb is what has to change."""
        found = morph.agreement_errors("Ma elab Tallinnas.")[0]
        assert "Ma elab Tallinnas."[found.start:found.end] == "elab"


class TestItDoesNotInventErrors:
    """The cost of a false positive is a learner told correct Estonian is
    wrong, which is worse than no checker at all."""

    @pytest.mark.parametrize("text", [
        "Ma elan Tallinnas.",
        "Sa elad seal.",
        "Ta elab kodus.",
        "Me elame siin.",
        "Te elate seal.",
        "Nad elavad siin.",
        "Ta on kodus.",
        "Ma olen õpilane ja ta on õpetaja.",
    ])
    def test_correct_estonian_is_left_alone(self, text):
        assert morph.agreement_errors(text) == []

    @pytest.mark.parametrize("text", ["Sa elasid seal.", "Sa elaksid seal.",
                                      "Nad elasid seal.", "Nad elaksid seal."])
    def test_a_form_ambiguous_between_two_persons_agrees_with_both(self, text):
        """`sid` and `ksid` are 2sg and 3pl: `sa elasid` is correct."""
        assert morph.agreement_errors(text) == []

    def test_negation_carries_no_person_and_is_not_checked(self):
        """`ma ei ela` is `ei` plus a connegative. It needs no special case and
        gets none: the connegative is not a finite personal form."""
        assert morph.agreement_errors("Ma ei ela siin.") == []

    @pytest.mark.parametrize("text", ["Eks ma ela siin.", "Ega ta tule."])
    def test_eks_and_ega_suppress_the_check(self, text):
        """They flip the clause to the imperative, where person marking stops
        applying. GiellaLT excludes them explicitly."""
        assert morph.agreement_errors(text) == []

    def test_only_the_immediately_following_word_is_judged(self):
        """Nothing is claimed about a verb that merely shares a sentence with
        a pronoun — that would need syntax, which this project does not have."""
        assert morph.agreement_errors("Ma tean, et ta elab siin.") == []


class TestTheTagTableMatchesVabamorf:
    """The person/form table is read off Vabamorf rather than a grammar book,
    so this regenerates it and fails if the two ever part company."""

    PRONOUNS = ("Ma", "Sa", "Ta", "Me", "Te", "Nad")

    @pytest.mark.parametrize("group", morph._FINITE)
    def test_every_tag_in_the_table_synthesises(self, group):
        from estnltk.vabamorf.morf import synthesize

        for tag in group:
            assert synthesize("elama", tag, "V"), tag

    def test_each_persons_present_form_agrees_with_its_own_pronoun(self):
        from estnltk.vabamorf.morf import synthesize

        for pronoun, tag in zip(self.PRONOUNS, morph._FINITE[0]):
            verb = synthesize("elama", tag, "V")[0]
            assert morph.agreement_errors(f"{pronoun} {verb} siin.") == [], (
                f"{pronoun} {verb}")


class TestItReachesTheLearner:
    def test_it_is_merged_into_whatever_the_chain_answered(self):
        """Deterministic evidence is added to a provider's answer, never raced
        against it — the same rule that put spelling there."""
        class _Answering:
            name = "pretend-llm"

            def available(self):
                return True

            def check(self, text):
                return grammar.GrammarResult(self.name, [])

        answer = grammar.check("Ma elab Tallinnas.", providers=[_Answering()])
        assert [(c.wrong, c.correct) for c in answer.corrections] == [
            ("elab", "elan")]
        assert answer.engine == "pretend-llm"

    def test_it_is_tagged_so_the_error_log_can_group_it(self):
        from eesti.config import TAGS

        found = grammar.agreement("Ma elab Tallinnas.")
        assert found[0].tag == "verb-form"
        assert found[0].tag in TAGS

    def test_it_explains_in_russian_and_keeps_the_estonian_term(self):
        why = grammar.agreement("Ma elab Tallinnas.")[0].why
        assert "pöördelõpp" in why.casefold()
        assert any("Ѐ" <= ch <= "ӿ" for ch in why), "must be Russian"
        assert "elan" in why, "and must name the form that belongs there"
