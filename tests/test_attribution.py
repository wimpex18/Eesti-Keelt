"""Crediting the sources whose words are on the screen.

EKI's terms (CC BY 4.0) require the reference to EKI to be kept and changes
described wherever the material is presented. The word card shows EKI's text
verbatim, so the API names whose definition it returned and the page draws the
credit.
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
        """`definition_source` is stated, not inferred: a PSV row with examples and no
        definition falls back to the live wording.
        """
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


class TestTheLedgerHasAReader:
    """`/api/sources` serves the ledger so the page can name sources and changes."""

    def test_the_route_serves_the_whole_ledger(self, client):
        from eesti.sources import REGISTRY

        got = client.get("/api/sources").json()
        assert len(got["sources"]) == len(REGISTRY)
        assert {s["id"] for s in got["sources"]} == {s.id for s in REGISTRY}

    def test_every_cc_by_source_describes_its_changes(self):
        """Every CC BY source states its changes."""
        from eesti.sources import REGISTRY

        for s in REGISTRY:
            if s.licence.upper().startswith("CC-BY"):
                assert s.changes, f"{s.id} is {s.licence} and says no changes"

    def test_changes_are_only_claimed_where_a_licence_asks(self):
        """Printing "no changes made" under a source we merely link to would
        turn a legal statement into decoration."""
        from eesti.sources import REGISTRY

        for s in REGISTRY:
            if s.changes:
                assert s.licence.upper().startswith("CC-BY"), s.id

    def test_the_route_flags_which_ones_oblige_the_page(self, client):
        got = client.get("/api/sources").json()
        assert set(got["attribution_required"]) == {
            "eki-tasemesonavara", "eki-psv", "eki-evs", "eki-har", "eki-vsl",
            "eki-ekss", "ekilex", "ekilex-wordlist"}

    def test_it_answers_without_a_corpus(self, client, monkeypatch, tmp_path):
        """Read from REGISTRY in code, not from the `sources` table. An
        unharvested deployment still has to be able to credit EKI, whose
        material is in the image rather than in the corpus."""
        from eesti import config

        monkeypatch.setattr(config, "CONTENT_DB", tmp_path / "absent.db")
        assert len(client.get("/api/sources").json()["sources"]) > 0

    def test_it_serves_no_material_and_nothing_about_the_learner(self, client):
        """A public-ish surface: keep it to facts that are already public."""
        allowed = {"id", "name", "kind", "licence", "url", "redistributable",
                   "changes"}
        for s in client.get("/api/sources").json()["sources"]:
            assert set(s) <= allowed, set(s) - allowed


class TestTheChangeDescriptionsAreReadable:
    """Change descriptions are Russian: they are explanation shown under a Russian
    heading.
    """

    def test_they_are_written_in_russian(self):
        import re

        from eesti.sources import REGISTRY

        for s in REGISTRY:
            if not s.changes:
                continue
            assert re.search(r"[а-яА-Я]", s.changes), (
                f"{s.id}: the change description has no Cyrillic in it")

    def test_they_do_not_name_columns_at_the_learner(self):
        """Change descriptions describe what was done to the dictionary, not schema
        details.
        """
        from eesti.sources import REGISTRY

        for s in REGISTRY:
            assert "`" not in s.changes, f"{s.id} shows code punctuation"
            assert "level_source" not in s.changes, s.id
