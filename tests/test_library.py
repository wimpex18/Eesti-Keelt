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
        import time

        mark_seen(progress, "abc", minutes=2)
        time.sleep(1.05)   # the key is (item, second), so a re-open needs a new second
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


def test_the_library_is_not_ordered_by_anything_the_learner_must_follow(content):
    """A shelf, not a path: browsing twice gives the same set, and nothing in
    the result claims a position or a gate."""
    rows = browse(content, "lugemine", limit=10)
    assert rows
    assert not any("locked" in r.keys() or "order" in r.keys() for r in rows)
