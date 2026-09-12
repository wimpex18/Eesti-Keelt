"""Crediting the sources whose words are on the screen.

EKI publish both files this app imports under CC BY 4.0, and their terms —
quoted on `arhiiv.eki.ee/litsents/` and again on `ekilex.ee` — are that the
material may be processed and presented in any way needed **provided** the
reference to EKI is retained and any modifications are described.

The word card renders EKI's definition and EKI's usage examples verbatim. The
credit for that lived in `docs/` and in a `sources.REGISTRY` note, and neither
is served to anybody: the registry was a licence ledger with no reader, which
is the same defect as a writer with no caller, pointing the other way.

So the API has to be able to say *whose* definition it just returned, and the
card has to draw it.
"""

from __future__ import annotations

import pathlib

import pytest

from eesti import psv, wordlist

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def words_db(tmp_path, monkeypatch):
    """A words database carrying two PSV rows, and nothing else."""
    from eesti import config

    path = tmp_path / "eesti.db"
    conn = wordlist.connect(path)
    psv.store(conn, [
        psv.Entry(lemma="raamat", definition="kokku köidetud lehed",
                  examples=("Huvitav raamat.",), pos="s"),
        # A real shape in EKI's file: examples, no definition.
        psv.Entry(lemma="ainultnaide", definition=None,
                  examples=("Ainult näide.",), pos="s"),
    ])
    conn.commit()
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.setattr(config, "VOCAB_DB", tmp_path / "vocab.db")
    return path


class TestTheApiNamesWhoAnswered:
    def test_ekis_wording_is_labelled_as_ekis(self, client, words_db):
        got = client.get("/api/enrich/raamat").json()
        assert got["definition"] == "kokku köidetud lehed"
        assert got["definition_source"] == "eki-psv"

    def test_sonaveebs_wording_is_labelled_as_sonaveebs(self, client, words_db):
        """A word EKI's 6 000 do not cover — the common case."""
        got = client.get("/api/enrich/helikopter").json()
        assert got["definition_source"] in (None, "sonapi")
        assert got["definition_source"] != "eki-psv"

    def test_an_examples_only_row_falls_back_instead_of_going_blank(
        self, client, words_db
    ):
        """The bug this field replaced an inference with.

        `definition_source` used to be deducible from `full_definition` being
        non-null, and the expression behind it read "PSV's definition if there
        is a PSV row at all" — so a row with examples and no definition
        returned `None` rather than the wording Sõnaveeb had. Asking which
        source answered, rather than deducing it, cannot make that mistake."""
        got = client.get("/api/enrich/ainultnaide").json()
        assert got["examples"] == ["Ainult näide."]
        assert got["definition_source"] != "eki-psv", "EKI said nothing here"

    def test_the_fuller_wording_is_offered_but_never_duplicated(
        self, client, words_db
    ):
        """`full_definition` is Sõnaveeb's, and only when it adds something."""
        got = client.get("/api/enrich/raamat").json()
        assert got["full_definition"] != got["definition"]


class TestTheCardDrawsTheCredit:
    @pytest.fixture
    def card(self):
        return (ROOT / "eesti" / "web" / "js" / "vocab.js").read_text(
            encoding="utf-8")

    def test_it_credits_eki_when_eki_answered(self, card):
        assert 'definition_source === "eki-psv"' in card
        assert "EKI põhisõnavara sõnastik" in card
        assert "CC BY 4.0" in card

    def test_the_credit_is_conditional_not_a_footer(self, card):
        """Crediting EKI under Sõnaveeb's wording would be a false statement
        about who wrote it, which is worse than crediting nobody."""
        credit = card.index("EKI põhisõnavara sõnastik")
        guard = card.index('definition_source === "eki-psv"')
        assert guard < credit
        assert credit - guard < 200, "the guard must belong to this line"

    def test_it_has_somewhere_to_be_drawn(self):
        css = (ROOT / "eesti" / "web" / "app.css").read_text(encoding="utf-8")
        assert ".meaning .attrib" in css
