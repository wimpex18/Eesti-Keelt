"""The one screen, and the number it refuses to show."""

from __future__ import annotations


import pytest

from eesti.overview import overview
from eesti.progress import connect as progress_connect
from eesti.progress import mark_mastered
from eesti.review import connect as review_connect
from eesti.vocab import connect as vocab_connect
from eesti.wordlist import connect as wordlist_connect


@pytest.fixture
def dbs(tmp_path):
    return {
        "progress": progress_connect(tmp_path / "p.db"),
        "reviews": review_connect(tmp_path / "r.db"),
        "vocabulary": vocab_connect(tmp_path / "v.db"),
        "words": wordlist_connect(),
    }


def test_there_is_no_overall_percentage(dbs):
    """The exam scores four parts separately and fails you for a zero in any
    one, so an aggregate would hide the thing that decides the outcome."""
    data = overview(**dbs)
    assert "overall" not in data["sections"]
    for section in data["sections"].values():
        assert "total_progress" not in section
    assert "no overall percentage" in data["note"]


def test_each_section_reports_its_own_measure(dbs):
    data = overview(**dbs)["sections"]
    assert {"mastered", "total", "next"} <= set(data["rada"])
    assert "bands" in data["sonavara"]
    assert {"due", "scheduled"} <= set(data["kordamine"])
    assert {"items", "minutes"} <= set(data["raamatukogu"])


def test_it_reflects_progress(dbs):
    before = overview(**dbs)["sections"]["rada"]["mastered"]
    mark_mastered(dbs["progress"], "kusisonad", via="placement")
    assert overview(**dbs)["sections"]["rada"]["mastered"] == before + 1


def test_every_connection_is_optional():
    """A learner who has never opened the library should see zero, not an app
    that refuses to render."""
    got = overview()
    assert got["sections"] == {}
    # The caveat is unconditional: it explains why there is no total, and that
    # is true with no data at all.
    assert got["caveat"]
    partial = overview(progress=progress_connect(":memory:"))
    assert "rada" in partial["sections"]
    assert "sonavara" not in partial["sections"]


def test_library_availability_is_included_when_content_is_given(tmp_path):
    from eesti.sources import Item, add_items, connect, register

    content = connect(tmp_path / "c.db")
    register(content)
    add_items(content, [Item("selges-keeles", "lugemine", body="Tekst.")])
    data = overview(content=content)
    assert data["sections"]["raamatukogu"]["available"]["lugemine"] == 1


def test_the_caveat_is_in_russian():
    """The project rule: Estonian for labels and grammar terms, Russian for
    anything that has to be understood. This sentence is the whole reason
    there is no single percentage — in Estonian it went unread."""
    caveat = overview()["caveat"]
    assert any("Ѐ" <= ch <= "ӿ" for ch in caveat)


def test_the_resume_topic_is_named_not_just_keyed(dbs):
    """The status screen names the next topic, not its id."""
    rada = overview(progress=dbs["progress"])["sections"]["rada"]
    assert rada["next"]
    assert rada["next_et"] and rada["next_et"] != rada["next"]
    assert any("Ѐ" <= ch <= "ӿ" for ch in rada["next_ru"])


def test_glossed_counts_every_offline_source_within_the_top_words(tmp_path):
    """"315 слов с переводом" counted only the seed and live store, while EKI's
    Estonian–Russian dictionary covers most of the list (DEV-49)."""
    from eesti import evs

    words = wordlist_connect(tmp_path / "w.db")
    words.executemany("INSERT INTO words(word, freq_rank, proficiency, pos) VALUES (?,?,?,?)",
                      [("siin", 1, "A1", "adv"), ("zzzx", 2, "A1", "s"), ("tee", 3, "A1", "s")])
    evs.store(words, [evs.Entry("siin", "adv", ("здесь",))])
    got = overview(vocabulary=vocab_connect(tmp_path / "v.db"), words=words)
    sonavara = got["sections"]["sonavara"]
    # `siin` from EVS, `tee` from the shipped seed; `zzzx` has no Russian.
    assert (sonavara["glossed"], sonavara["glossed_of"]) == (2, 3)


def test_the_card_says_glossed_out_of_the_ranked_words():
    from pathlib import Path

    page = (Path(__file__).resolve().parents[1] / "eesti/web/js/path.js").read_text("utf-8")
    assert "с переводом: ${s.sonavara.glossed} из ${s.sonavara.glossed_of}" in page
