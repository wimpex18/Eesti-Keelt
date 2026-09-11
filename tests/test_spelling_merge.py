"""Vabamorf's dictionary does not lose to a model's opinion.

`check()` returns the **first** provider that answers, which was quietly
breaking this project's central rule. The moment an LLM lane is configured it
answers — so Vabamorf's spelling verdict was thrown away on every request.

And the LLM does not cover for it. The prompt it ships with is aimed at object
case and says in as many words that most text is already correct and to report
a correction only where one of those rules is broken. `tanav` for `tänav`
breaks none of them, so nothing in the chain reported the single commonest way
a Russian speaker mistypes Estonian: a missing täpitäht.
"""

from __future__ import annotations

import pytest

from eesti.providers import grammar

TEXT = "Ma ostsin uue autot ja laksin tanav peale."


class _Answering:
    """A provider that answers about grammar and says nothing about spelling —
    the shape of every LLM lane in the chain."""

    name = "pretend-llm"

    def __init__(self, corrections=()):
        self._corrections = list(corrections)

    def available(self) -> bool:
        return True

    def check(self, text: str) -> grammar.GrammarResult:
        return grammar.GrammarResult(self.name, list(self._corrections))


class _Dead:
    name = "pretend-dead"

    def available(self) -> bool:
        return True

    def check(self, text: str) -> grammar.GrammarResult:
        raise OSError("500 after 61s, which is what the real one does")


class TestTheDictionaryIsAlwaysConsulted:
    def test_spelling_survives_a_provider_that_answered(self):
        answer = grammar.check(TEXT, providers=[_Answering([
            grammar.Correction("autot", "auto", "Täissihitis.", "obj-case"),
        ])])
        found = {(c.wrong, c.correct) for c in answer.corrections}
        assert ("autot", "auto") in found, "the provider's own answer is kept"
        assert ("tanav", "tänav") in found, "and the dictionary's is added"

    def test_the_engine_is_still_the_one_that_answered(self):
        """Merging evidence must not claim a different engine answered."""
        answer = grammar.check(TEXT, providers=[_Answering()])
        assert answer.engine == "pretend-llm"
        assert not answer.degraded

    def test_it_reaches_past_a_dead_provider(self):
        answer = grammar.check(TEXT, providers=[_Dead(), _Answering()])
        assert any(c.wrong == "tanav" for c in answer.corrections)

    def test_the_provider_keeps_the_word_it_already_explained(self):
        """A provider's explanation has a reason attached; this one only has
        "not in the dictionary". The better explanation wins, and the word is
        not reported twice."""
        answer = grammar.check(TEXT, providers=[_Answering([
            grammar.Correction("tanav", "tänav", "Пропущена täpitäht ä.", "vocab"),
        ])])
        hits = [c for c in answer.corrections if c.wrong == "tanav"]
        assert len(hits) == 1
        assert hits[0].why == "Пропущена täpitäht ä."

    def test_the_offline_fallback_does_not_double_report(self):
        """It already runs the same spellcheck itself."""
        answer = grammar.check(TEXT, providers=[grammar.VabamorfFallback()])
        assert len([c for c in answer.corrections if c.wrong == "tanav"]) == 1

    def test_correct_estonian_gains_nothing(self):
        answer = grammar.check(
            "Ma lugesin raamatu läbi.", providers=[_Answering()])
        assert answer.corrections == []

    def test_nothing_answering_is_still_reported_as_nothing(self):
        """A spellcheck must never be dressed up as a working grammar service:
        if every provider failed, the honest answer is that none answered."""
        answer = grammar.check(TEXT, providers=[_Dead()])
        assert answer.engine == "none"
        assert answer.degraded
        assert answer.corrections == []


class TestWhatTheDictionaryActuallyCatches:
    @pytest.mark.parametrize(("wrong", "right"), [
        ("tanav", "tänav"),
        ("kirjutamien", "kirjutamine"),
    ])
    def test_it_suggests_the_word_that_was_meant(self, wrong, right):
        got = {c.wrong: c.correct for c in grammar.spelling(f"See on {wrong} siin.")}
        assert got.get(wrong) == right

    def test_it_is_located_so_the_page_can_highlight_it(self):
        found = grammar.spelling(TEXT)
        assert found and all(c.start is not None for c in found)
        assert TEXT[found[0].start:found[0].end] == found[0].wrong

    def test_it_explains_in_russian_and_names_its_authority(self):
        """The language rule: everything explaining or warning is Russian. And
        "not in the dictionary" from Vabamorf is a different kind of claim from
        "I think this is wrong" from a model — the learner can tell them
        apart."""
        why = grammar.SPELLING_WHY
        assert "Vabamorf" in why
        assert any("Ѐ" <= ch <= "ӿ" for ch in why), "must be Russian"

    def test_the_offline_provider_locates_its_spelling_too(self):
        """Found end to end, through the real endpoint, not by a test.

        `VabamorfFallback` built its own unlocated `Correction`s, so every
        misspelling it reported arrived with `start`/`end` of `None` and the
        page had nothing to highlight. It survived the merge as well: a word
        the provider already named is the one the merge keeps, so the located
        copy lost to the unlocated one.
        """
        text = "See on tanav siin."
        answer = grammar.check(text, providers=[grammar.VabamorfFallback()])
        found = [c for c in answer.corrections if c.wrong == "tanav"]
        assert len(found) == 1
        assert found[0].start is not None, "the page cannot highlight None"
        assert text[found[0].start:found[0].end] == "tanav"

    def test_it_needs_no_network(self, monkeypatch):
        """The whole point: this answers when everything else is down."""
        def boom(*a, **k):
            raise AssertionError("spelling must not leave the machine")

        monkeypatch.setattr("urllib.request.urlopen", boom)
        assert grammar.spelling(TEXT)
