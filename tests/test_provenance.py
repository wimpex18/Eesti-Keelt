"""Every correction says who stands behind it, and only what code can vouch for
reaches the error log (`providers/grammar.verify`, ADR-1).
"""

from __future__ import annotations

import pytest

from eesti.providers.grammar import Correction, agreement, spelling, verify


def _one(text: str, wrong: str, correct: str, tag: str = "vocab") -> str:
    return verify(text, [Correction(wrong, correct, "x", tag=tag)])[0].source


class TestWhatCodeDecides:
    def test_the_deterministic_checks_say_so(self):
        pytest.importorskip("estnltk")
        found = spelling("Ma armastan eesti kel.") + agreement("Ma elab siin.")
        assert found and all(c.source == "deterministic" for c in found)

    def test_a_deterministic_correction_is_never_downgraded(self):
        c = Correction("x", "y", "why", tag="vocab", source="deterministic")
        assert verify("Ma elan siin.", [c])[0].source == "deterministic"


class TestWhatCodeCanCheck:
    def test_a_form_of_the_same_word_is_verifiable(self):
        pytest.importorskip("estnltk")
        assert _one("Ma näen kass.", "kass", "kassi") == "model+verified"

    def test_a_real_word_replacing_a_non_word_is_verifiable(self):
        pytest.importorskip("estnltk")
        assert _one("Eile ma teesin tööd.", "teesin", "tegin",
                    tag="verb-form") == "model+verified"

    def test_a_suggestion_estonian_does_not_have_is_not(self):
        pytest.importorskip("estnltk")
        assert _one("Ma elan siin.", "elan", "elanik-xyz") == "model-only"

    def test_a_reordering_is_not_checkable(self):
        assert _one("Eile ma käisin poes.", "ma käisin", "käisin ma",
                    tag="word-order") == "model-only"


class TestObjectCase:
    """The documented #1 weakness: only the rule code owns counts as checked."""

    def test_partitive_after_a_negation_is_verifiable(self):
        pytest.importorskip("estnltk")
        assert _one("Ma ei ostnud pileti.", "pileti", "piletit",
                    tag="obj-case") == "model+verified"

    def test_an_aspect_swap_is_a_judgement_the_app_does_not_make(self):
        pytest.importorskip("estnltk")
        assert _one("Ma lugesin raamatut läbi.", "raamatut", "raamatu",
                    tag="obj-case") == "model-only"

    def test_a_negation_in_another_clause_governs_nothing(self):
        pytest.importorskip("estnltk")
        text = "Ma ei ostnud pileti ja ma lugesin raamatu."
        got = verify(text, [Correction("raamatu", "raamatut", "x", tag="obj-case")])
        assert got[0].source == "model-only"


class TestTheErrorLog:
    @pytest.fixture
    def client(self):
        pytest.importorskip("httpx2")
        from fastapi.testclient import TestClient

        from eesti.app import app

        return TestClient(app)

    def test_a_model_only_correction_is_refused(self, client):
        r = client.post("/api/notion/queue", json={
            "wrong": "raamatut", "correct": "raamatu", "tag": "obj-case",
            "source": "model-only"})
        assert r.status_code == 400 and "model-only" in r.json()["detail"]

    @pytest.mark.parametrize("source", ["deterministic", "model+verified"])
    def test_what_code_vouches_for_is_queued(self, client, source):
        r = client.post("/api/notion/queue", json={
            "wrong": "pileti", "correct": "piletit", "tag": "obj-case",
            "source": source})
        assert r.status_code == 200 and r.json()["queued"]


def test_locating_a_spelling_correction_preserves_its_authority():
    from eesti.providers.grammar import _locate
    correction = Correction('kel', 'keel', 'dictionary', source='deterministic')
    located = _locate('eesti kel', [correction])[0]
    assert located.source == 'deterministic' and located.start == 6


@pytest.mark.parametrize('tag', ['vocab', 'obj-case'])
def test_provider_tag_or_verified_claim_cannot_launder_an_aspect_judgement(tag):
    correction = Correction('raamatut', 'raamatu', 'model', tag=tag, source='model+verified')
    assert verify('Ma lugesin raamatut läbi.', [correction])[0].source == 'model-only'


def test_deterministic_agreement_wins_over_a_conflicting_model_suggestion():
    from eesti.providers.grammar import GrammarResult, _merge_spelling
    result = GrammarResult('test', [Correction('elab', 'elas', 'model')])
    got = _merge_spelling('Ma elab siin.', result)
    correction = next(c for c in got.corrections if c.wrong == 'elab')
    assert correction.correct == 'elan' and correction.source == 'deterministic'
