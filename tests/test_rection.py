"""Verb government parsed from EKK's own list of error-prone rections.

The parser's job is mostly refusal. EKK's table is prose written for humans:
some entries list two correct frames, some license the starred case elsewhere in
the same row, and some are not case frames at all. Every one of those, drilled
naively, marks a correct answer wrong.
"""

from __future__ import annotations

import sqlite3

import pytest

from eesti import cloze, rection


def _table(rows: list[tuple[str, str]]) -> str:
    cells = "".join(
        f"<tr><TD><I>{head}</I></TD><TD>{frame}</TD><TD><I>x</I></TD></TR>"
        for head, frame in rows
    )
    return f"<h3>{rection.SECTION}</h3><TABLE>{cells}</TABLE><p>Üldlaiend"


def test_a_clean_contrast_is_extracted():
    got = rection.parse(_table([("kohanema", "millega (*millele)")]))
    assert len(got) == 1
    assert got[0].headword == "kohanema"
    assert (got[0].correct_case, got[0].wrong_case) == ("sg kom", "sg all")


def test_two_correct_frames_are_refused():
    """`sarnane mille/millega (*millele)` — both are right, so a drill that
    accepts one of them marks the other wrong."""
    assert rection.parse(_table([("sarnane", "mille/millega (*millele)")])) == []


def test_a_frame_licensed_again_in_the_tail_is_refused():
    """`kindel milles (*millele) kellele ~ kelle peale` stars the allative for
    things and then allows it for people. That is a contradiction, not a
    contrast."""
    assert rection.parse(
        _table([("kindel", "milles (*millele) kellele ~ kelle peale")])
    ) == []


def test_non_case_frames_are_refused():
    """`millal`, `mis ajast` and postpositions are real rules but not case
    contrasts; forcing them into a case slot would teach something false."""
    assert rection.parse(_table([("algama", "millal (*mis ajast)")])) == []
    assert rection.parse(
        _table([("kohustus", "kelle/mille vastu (russitsism *ees)")])
    ) == []


def test_entries_with_no_marked_error_are_skipped():
    """Without a starred form there is no documented wrong answer, and this
    module refuses to invent one."""
    assert rection.parse(_table([("allkirjastama", "mis/mille/mida")])) == []


def test_same_case_on_both_sides_is_not_drillable():
    assert rection.Rection("x", "mida", "keda", "sg p", "sg p").drillable is False


def test_missing_section_yields_nothing_rather_than_garbage():
    assert rection.parse("<html><TABLE><tr><TD>x</TD></tr></TABLE></html>") == []


def test_store_round_trips(tmp_path):
    conn = sqlite3.connect(tmp_path / "c.db")
    conn.row_factory = sqlite3.Row
    rows = rection.parse(_table([("kohanema", "millega (*millele)")]))
    assert rection.store(conn, rows) == 1
    got = conn.execute("SELECT * FROM rections").fetchone()
    assert got["headword"] == "kohanema" and got["correct_case"] == "sg kom"


@pytest.fixture
def words(tmp_path):
    conn = sqlite3.connect(tmp_path / "w.db")
    conn.executescript(
        "CREATE TABLE words (word TEXT PRIMARY KEY, freq_rank INT,"
        " proficiency TEXT, pos TEXT);"
    )
    conn.executemany(
        "INSERT INTO words VALUES (?,?,?,?)",
        [("kohanema", 1, "B1", "v"), ("baseeruma", 2, "B2", "v"),
         ("otsus", 3, "A2", "s"), ("naaber", 4, "A2", "s")],
    )
    conn.commit()
    return conn


def test_level_filter_keeps_the_learner_out_of_b2_vocabulary(words):
    rows = [
        rection.Rection("kohanema", "millega", "millele", "sg kom", "sg all"),
        rection.Rection("baseeruma", "millel", "millele", "sg ad", "sg all"),
    ]
    kept = rection.at_levels(words, rows, ("A1", "A2", "B1"))
    assert [r.headword for r in kept] == ["kohanema"]
    assert len(rection.at_levels(words, rows, ("A1", "A2", "B1", "B2"))) == 2


class TestRectionDrills:
    ROWS = [rection.Rection("kohanema", "millega", "millele", "sg kom", "sg all")]

    def test_both_forms_are_real_and_different(self, words):
        items = cloze.rection_clozes(self.ROWS, words=words, seed=1)
        assert items
        for item in items:
            assert item.answer != item.distractor
            assert item.check(item.answer) and not item.check(item.distractor)

    def test_the_prompt_does_not_give_the_case_away(self, words):
        """For rection the case *is* the question, unlike case-production items
        where naming it is what makes the answer unique."""
        for item in cloze.rection_clozes(self.ROWS, words=words, seed=1):
            assert item.case_et not in item.hint
            assert item.governor == "kohanema"

    def test_items_are_filed_under_the_rection_topic(self, words):
        for item in cloze.rection_clozes(self.ROWS, words=words, seed=1):
            assert item.topic == "rektsioon"
            assert item.reference["ekk_section"] == "SÜ 64"

    def test_impersonal_verbs_do_not_get_a_personal_subject(self, words):
        rows = [rection.Rection("põhinema", "millel", "millele", "sg ad", "sg all")]
        for item in cloze.rection_clozes(rows, words=words, seed=1):
            assert item.prompt.startswith("See ")

    def test_a_person_frame_selects_a_person_noun(self, words):
        rows = [rection.Rection("teavitama", "keda", "kellele", "sg p", "sg all")]
        for item in cloze.rection_clozes(rows, words=words, seed=1):
            assert item.lemma in cloze._PEOPLE

    def test_adjective_headwords_use_a_copula_frame(self, words):
        rows = [rection.Rection("lähedane", "millele", "millega", "sg all", "sg kom")]
        for item in cloze.rection_clozes(rows, words=words, seed=1):
            assert item.prompt.startswith("See on ") and item.prompt.endswith("lähedane.")
