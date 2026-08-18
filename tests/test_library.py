"""The library surface, and the measures that must not become mastery."""

from __future__ import annotations

import sqlite3

import pytest

from eesti import library
from eesti.library import SECTIONS, browse, exposure, mark_seen, sections
from eesti.progress import connect as progress_connect


@pytest.fixture
def content(tmp_path):
    from eesti.sources import Item, add_items, connect, register

    conn = connect(tmp_path / "c.db")
    register(conn)
    add_items(conn, [
        Item("selges-keeles", "lugemine", body="Ma elan Tallinnas.", title="Text A",
             level="kerge"),
        Item("selges-keeles", "lugemine", body="Ta läks kooli.", title="Text B",
             level="raske"),
        Item("err-r4", "kuulamine", body="", title="Episode 1",
             audio_url="https://example.invalid/a.mp3"),
        Item("err-r4", "grammatika", body="Transcript", title="Lesson 1",
             audio_url="https://example.invalid/b.mp3"),
        Item("generated", "lugemine", body="Genereeritud tekst.", title="Public one"),
    ])
    return conn


@pytest.fixture
def progress(tmp_path):
    return progress_connect(tmp_path / "p.db")


def test_every_section_maps_to_a_real_skill():
    from eesti.sources import SKILLS

    for section in SECTIONS:
        assert section.skills
        assert set(section.skills) <= set(SKILLS), section.id


def test_sections_count_what_is_there(content):
    counts = {s["id"]: s["items"] for s in sections(content)}
    assert counts["lugemine"] == 3
    assert counts["kuulamine"] == 1
    assert counts["saated"] == 1


def test_audio_is_counted_separately(content):
    by_id = {s["id"]: s for s in sections(content)}
    assert by_id["kuulamine"]["with_audio"] == 1
    assert by_id["lugemine"]["with_audio"] == 0


class TestLicenceGating:
    def test_public_view_shows_only_redistributable_sources(self, content):
        """A filter on the source's licence, not on the item — so a new source
        cannot leak by forgetting to tag its rows."""
        counts = {s["id"]: s["items"] for s in sections(content, public_only=True)}
        assert counts["lugemine"] == 1      # the generated one
        assert counts["kuulamine"] == 0     # (c) ERR
        assert counts["saated"] == 0

    def test_browsing_publicly_never_returns_owner_only_material(self, content):
        for section in ("lugemine", "kuulamine", "saated"):
            for row in browse(content, section, public_only=True, limit=50):
                assert row["redistributable"] == 1


class TestExposure:
    def test_opening_material_is_recorded(self, progress):
        mark_seen(progress, "abc", minutes=4.5)
        assert exposure(progress) == {"openings": 1, "items": 1, "minutes": 4.5}

    def test_reopening_counts_time_without_double_counting_the_item(self, progress):
        """Two opens in the same second must both count.

        This test used to sleep 1.05s, which was it accommodating a bug: the
        primary key was (item_id, seen_at) at second granularity, so the second
        open REPLACEd the first and its minutes were *lost*. A test that has to
        wait to observe correct behaviour is describing the defect, not the
        requirement.
        """
        mark_seen(progress, "abc", minutes=2)
        mark_seen(progress, "abc", minutes=3)
        got = exposure(progress)
        assert got["items"] == 1 and got["openings"] == 2 and got["minutes"] == 5.0

    def test_exposure_reports_no_percentage(self, progress):
        """There is no honest denominator: the library grows, and "12 % of the
        library" says nothing about whether the learner can read."""
        mark_seen(progress, "abc")
        assert not any("percent" in k or "share" in k for k in exposure(progress))

    def test_seen_items_are_listed(self, progress):
        mark_seen(progress, "a")
        mark_seen(progress, "b")
        assert library.seen_items(progress) == {"a", "b"}


def test_a_multi_skill_section_reaches_every_skill(content):
    """`eksam` covers writing and speaking. Asking each skill for `limit` rows
    and truncating meant that with eight writing tasks and a limit of five, no
    speaking task was ever reachable."""
    from eesti.sources import Item, add_items

    add_items(content, [
        Item("harno", "kirjutamine", body=f"w{i}", title=f"W{i}") for i in range(8)
    ] + [
        Item("harno", "raakimine", body=f"s{i}", title=f"S{i}") for i in range(3)
    ])
    skills = {r["skill"] for r in browse(content, "eksam", limit=5)}
    assert skills == {"kirjutamine", "raakimine"}


def test_browse_respects_the_limit(content):
    assert len(browse(content, "lugemine", limit=2)) == 2


def test_the_library_is_not_ordered_by_anything_the_learner_must_follow(content):
    """A shelf, not a path: browsing twice gives the same set, and nothing in
    the result claims a position or a gate."""
    rows = browse(content, "lugemine", limit=10)
    assert rows
    assert not any("locked" in r.keys() or "order" in r.keys() for r in rows)


class TestOpeningRecordsVocabulary:
    """The writer that was missing.

    `vocab.py` could measure coverage and `band_progress` could report known
    words per band, and nothing in the app ever wrote a word into that table —
    so both measured something permanently empty. The measurement had been
    built without the recording.
    """

    def test_opening_a_text_records_the_words_met(self, content, progress, tmp_path):
        from eesti.vocab import connect as vocab_connect

        vocabulary = vocab_connect(tmp_path / "v.db")
        item = browse(content, "lugemine", limit=1)[0]
        result = library.open_item(content, item["id"], progress, vocabulary)
        assert result["lemmas"] > 0
        tracked = vocabulary.execute("SELECT COUNT(*) FROM vocab_status").fetchone()[0]
        assert tracked == result["lemmas"]

    def test_encounters_are_not_knowledge(self, content, progress, tmp_path):
        """A word skimmed past is not a word learned — the mistake that makes
        automatic 'known' counts meaningless."""
        from eesti.vocab import KNOWN, WELL_KNOWN, connect as vocab_connect

        vocabulary = vocab_connect(tmp_path / "v.db")
        item = browse(content, "lugemine", limit=1)[0]
        library.open_item(content, item["id"], progress, vocabulary)
        known = vocabulary.execute(
            "SELECT COUNT(*) FROM vocab_status WHERE status IN (?,?)",
            (KNOWN, WELL_KNOWN),
        ).fetchone()[0]
        assert known == 0

    def test_it_records_exposure_too(self, content, progress, tmp_path):
        item = browse(content, "lugemine", limit=1)[0]
        library.open_item(content, item["id"], progress, minutes=2.5)
        assert exposure(progress)["minutes"] == 2.5

    def test_both_sides_are_optional(self, content):
        item = browse(content, "lugemine", limit=1)[0]
        assert library.open_item(content, item["id"])["lemmas"] == 0

    def test_an_unknown_item_is_an_error_not_a_silent_no_op(self, content):
        with pytest.raises(KeyError):
            library.open_item(content, "no-such-item")

    def test_opening_twice_counts_encounters_not_new_words(
        self, content, progress, tmp_path
    ):
        from eesti.vocab import connect as vocab_connect

        vocabulary = vocab_connect(tmp_path / "v.db")
        item = browse(content, "lugemine", limit=1)[0]
        library.open_item(content, item["id"], progress, vocabulary)
        before = vocabulary.execute("SELECT COUNT(*) FROM vocab_status").fetchone()[0]
        library.open_item(content, item["id"], progress, vocabulary)
        after = vocabulary.execute("SELECT COUNT(*) FROM vocab_status").fetchone()[0]
        assert after == before
        met = vocabulary.execute(
            "SELECT MAX(met_count) FROM vocab_status"
        ).fetchone()[0]
        assert met >= 2
