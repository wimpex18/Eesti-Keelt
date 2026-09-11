"""The TartuNLP GEC contract, pinned to their published OpenAPI spec.

`api.tartunlp.ai/grammar/openapi.json` is public and was read on 2026-09-11.
Both of its endpoints answer HTTP 500 after ~61 s — reproduced with the spec's
own example, `{"text": "Aitähh!"}` — so nothing here can be verified against a
live answer. What *can* be pinned is that when their worker comes back, this
app parses what they publish: these tests replay the two response shapes from
the spec and check the corrections that come out.

A `GET` to the same URL returns 405. That is the trap: the route exists and the
host is up, so a liveness check built on `GET` reports a healthy service that
has never once returned a correction.
"""

from __future__ import annotations

import pytest

from eesti.providers.grammar import TartuNLPGrammar, _minimal_span, _tag_of

TEXT = "Ma ostsin uue autot. Oktoobris vihmased päevad vahelduvad."

#: `GECResult_v2`: sentence pairs plus an Estonian explanation.
V2 = {"corrections": [
    {"original": "Ma ostsin uue autot.", "corrected": "Ma ostsin uue auto.",
     "correction_log": "...", "explanations": "Sihitis on täissihitis."},
    {"original": "Oktoobris vihmased päevad vahelduvad.",
     "corrected": "Oktoobris vahelduvad vihmased päevad.",
     "correction_log": "...", "explanations": ""},
]}

#: `GECResult`: character spans and replacements.
V1 = {"corrections": [
    {"span": {"start": 14, "end": 19, "value": "autot"},
     "replacements": [{"value": "auto"}]},
], "corrected_text": "Ma ostsin uue auto. Oktoobris vihmased päevad vahelduvad."}


class TestTheMinimalSpan:
    """`/v2` answers in whole sentences; a whole-sentence highlight tells a
    learner nothing. The one thing a correction must say is *which word*."""

    def test_one_changed_word_narrows_to_that_word(self):
        assert _minimal_span("Ma ostsin uue autot.", "Ma ostsin uue auto.") == (
            "autot", "auto")

    def test_a_shared_full_stop_is_not_part_of_the_mistake(self):
        assert _minimal_span("Ta tuli koju.", "Ta tuli kodu.") == ("koju", "kodu")

    def test_punctuation_that_did_change_survives(self):
        assert _minimal_span("Ta tuli koju", "Ta tuli koju.") == ("koju", "koju.")

    def test_an_insertion_keeps_the_whole_pair(self):
        """Trimming a pure insertion leaves nothing on one side, and a
        correction with an empty `wrong` can never be located."""
        wrong, right = _minimal_span("Ma lugesin raamatu.", "Ma lugesin raamatu läbi.")
        assert wrong and right

    def test_identical_input_is_left_alone(self):
        assert _minimal_span("Ma sõin suppi.", "Ma sõin suppi.") == (
            "Ma sõin suppi.", "Ma sõin suppi.")


class TestTheTag:
    """TartuNLP returns no error type, so everything was filed as `vocab` —
    and the Notion error log groups on that field."""

    def test_a_pure_reordering_is_tagged_word_order(self):
        assert _tag_of("Oktoobris vihmased päevad vahelduvad.",
                       "Oktoobris vahelduvad vihmased päevad.") == "word-order"

    def test_a_changed_word_stays_the_honest_default(self):
        assert _tag_of("Ma ostsin uue autot.", "Ma ostsin uue auto.") == "vocab"


class TestParsingWhatTheSpecPublishes:
    def test_v2_sentence_pairs_become_located_word_corrections(self):
        got = TartuNLPGrammar._from_v2(V2)
        assert [(c.wrong, c.correct) for c in got] == [
            ("autot", "auto"),
            ("vihmased päevad vahelduvad", "vahelduvad vihmased päevad"),
        ]
        assert got[0].why == "Sihitis on täissihitis."
        assert got[1].why == "(selgitus puudub)", "an empty explanation must say so"

    def test_v1_spans_arrive_already_located(self):
        got = TartuNLPGrammar._from_v1(V1)
        assert len(got) == 1
        assert (got[0].wrong, got[0].correct) == ("autot", "auto")
        assert (got[0].start, got[0].end) == (14, 19), (
            "the span endpoint gives offsets outright; re-deriving them would "
            "throw away the one thing it has that /v2 does not"
        )

    @pytest.mark.parametrize("payload", [{}, {"corrections": []}])
    def test_no_corrections_is_a_valid_answer_not_a_crash(self, payload):
        assert TartuNLPGrammar._from_v2(payload) == []
        assert TartuNLPGrammar._from_v1(payload) == []

    def test_a_replacement_identical_to_the_span_is_not_a_correction(self):
        same = {"corrections": [{"span": {"start": 0, "end": 2, "value": "Ma"},
                                 "replacements": [{"value": "Ma"}]}]}
        assert TartuNLPGrammar._from_v1(same) == []


class TestTheChain:
    def test_both_published_endpoints_are_tried(self):
        v2, root = TartuNLPGrammar.ENDPOINTS
        assert v2.endswith("/grammar/v2")
        assert root.endswith("/grammar/")

    def test_the_fallback_runs_when_v2_fails(self, monkeypatch):
        calls = []

        def fake_post(self, url, text):
            calls.append(url)
            if url.endswith("/v2"):
                raise OSError("500 after 61s, which is what it actually does")
            return V1

        monkeypatch.setattr(TartuNLPGrammar, "_post", fake_post)
        result = TartuNLPGrammar().check(TEXT)
        assert len(calls) == 2, "the span endpoint must be tried"
        assert [c.wrong for c in result.corrections] == ["autot"]
