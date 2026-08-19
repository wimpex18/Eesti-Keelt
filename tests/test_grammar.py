"""Grammar references and principal forms."""

import pytest

from eesti.config import TAGS
from eesti.grammar import REFERENCES, describe, reference_for
from eesti.lookup import principal_forms


class TestGrammarReferences:
    def test_the_documented_gaps_have_references(self):
        """The two tags the error log actually flags must be explainable."""
        for tag in ("obj-case", "verb-form"):
            ref = reference_for(tag)
            assert ref is not None
            assert ref.ekk_section and ref.url.startswith("https://arhiiv.eki.ee/")

    def test_every_reference_uses_a_real_error_tag(self):
        """References must key off the Notion tag vocabulary, not a parallel one."""
        assert set(REFERENCES) <= set(TAGS)

    def test_object_case_uses_the_proper_estonian_terms(self):
        """`obj-case` is our shorthand; an examiner says täissihitis/osasihitis."""
        ref = reference_for("obj-case")
        assert "täissihitis" in ref.et_term and "osasihitis" in ref.et_term

    def test_section_labels_match_the_chapter_they_link_to(self):
        """EKK numbers morphology `M` and syntax `SÜ`, on different chapter ids.

        A mismatch here is the signature of the bug this caught once already:
        a reference that resolves to a real handbook page carrying a different
        section. That is worse than a missing link, because it looks verified.
        """
        prefix = {3: "M ", 5: "SÜ "}
        for ref in REFERENCES.values():
            assert ref.chapter in prefix, ref.tag
            assert ref.ekk_section.startswith(prefix[ref.chapter]), ref.tag

    @pytest.mark.parametrize(
        "tag, section",
        [
            ("obj-case", "SÜ 37"),    # Sihitis: täis- ja osasihitis
            ("rektsioon", "SÜ 64"),   # Rektsioon
            ("word-order", "SÜ 90"),  # Lause sõnajärg
            ("gen-stem", "M 51"),     # Omastav kääne
            ("gradation", "M 22"),    # Astmevaheldus
            ("ma-da-inf", "M 73"),    # Infiniitsed vormid: da-tegevusnimi
        ],
    )
    def test_sections_are_the_ones_read_off_the_handbook(self, tag, section):
        """Pinned against the handbook's own contents, so a plausible-looking
        edit cannot quietly reintroduce a wrong number."""
        assert reference_for(tag).ekk_section == section

    def test_the_largest_learner_error_class_is_explainable(self):
        """Word order is 11.4 % of annotated errors in EVKK and had no entry."""
        ref = reference_for("word-order")
        assert ref is not None and ref.summary_ru

    def test_unknown_tags_report_unknown_rather_than_guessing(self):
        assert describe("not-a-tag") == {"tag": "not-a-tag", "known": False}


class TestPrincipalForms:
    @pytest.mark.parametrize(
        "lemma,citation",
        [
            ("raamat", "raamat, raamatu, raamatut"),
            ("sõber", "sõber, sõbra, sõpra"),      # consonant gradation
            ("pood", "pood, poe, poodi"),          # irregular stem
            ("tuba", "tuba, toa, tuba"),           # partitive == nominative
            ("maja", "maja, maja, maja"),          # all three identical
        ],
    )
    def test_citation_matches_dictionary_convention(self, lemma, citation):
        assert principal_forms(lemma)["citation"] == citation

    def test_words_with_no_contrast_are_flagged_as_such(self):
        """`maja` cites identically three times — nothing to drill there."""
        assert principal_forms("maja")["object_case_contrast"] is False
        assert principal_forms("raamat")["object_case_contrast"] is True

    def test_missing_words_are_reported_not_invented(self):
        assert principal_forms("zzzqqqxx")["found"] is False
