"""Three sections, and nothing homeless.

The app answers three questions and each section belongs to exactly one:

    õppimine  — "what am I learning today?"
    kordamine — "what am I forgetting?"
    eksam     — "am I ready?"

Sections used to filter on skill alone, and that held only while every item was
reading or listening practice. The official material broke it: HARNO publishes
samples, videos, workbooks and information sheets that carry the *same skill* as
a task while being a completely different activity. Twenty-five of them landed
in no section at all — in the database, absent from the app, and nothing said
so.

The test that matters here is the orphan check. A missing section is visible;
an item that belongs to none is not.
"""

from __future__ import annotations

import json

import pytest

from eesti.library import MODES, SECTIONS, browse, by_id, sections
from eesti.sources import Item, add_items, connect, register


@pytest.fixture
def shelf(tmp_path):
    """One item of each kind that has ever caused trouble."""
    conn = connect(tmp_path / "content.db")
    register(conn)
    sources = {r["id"] for r in conn.execute("SELECT id FROM sources")}
    made = [
        Item(source_id="selges-keeles", skill="lugemine", title="Lihtne tekst",
             body="Ma lugesin raamatu läbi."),
        Item(source_id="harno", skill="lugemine", title="B1 Lu1 kuulutus",
             body="", meta={"kind": "ulesanne", "external": True}),
        Item(source_id="harno", skill="kirjutamine", title="B1 sooritusnäidis",
             body="", meta={"kind": "sooritusnaidis", "external": True}),
        Item(source_id="harno", skill="eksam", title="B1 konsultatsioon",
             body="", meta={"kind": "konsultatsioon", "external": True}),
        Item(source_id="harno", skill="eksam", title="B1 video",
             body="", meta={"kind": "video", "external": True}),
        Item(source_id="err-r4", skill="grammatika", title="Saade 22",
             body="Objekti kääne."),
    ]
    add_items(conn, [i for i in made if i.source_id in sources])
    return conn


class TestNothingIsHomeless:
    def test_every_item_appears_in_some_section(self, shelf):
        """The check that a missing section would not give you."""
        placed: set[str] = set()
        for section in SECTIONS:
            placed |= {r["id"] for r in browse(shelf, section.id, limit=500)}
        everything = {r["id"] for r in shelf.execute("SELECT id FROM items")}
        assert everything - placed == set()

    def test_the_kinds_that_were_lost_are_reachable(self, shelf):
        """Samples, workbooks and videos: the 25 that vanished."""
        for section_id, expected in [("naidised", "sooritusnaidis"),
                                     ("vihikud", "konsultatsioon"),
                                     ("eksamiinfo", "video")]:
            rows = browse(shelf, section_id, limit=50)
            kinds = {json.loads(r["meta"] or "{}").get("kind") for r in rows}
            assert expected in kinds, section_id


class TestTheSectionsSeparate:
    def test_reading_practice_excludes_exam_tasks(self, shelf):
        """349 simple texts and 17 exam PDFs in one list served neither the
        person practising nor the person deciding whether to register."""
        rows = browse(shelf, "lugemine", limit=50)
        kinds = {json.loads(r["meta"] or "{}").get("kind") for r in rows}
        assert "ulesanne" not in kinds

    def test_exam_tasks_exclude_everything_that_is_not_a_task(self, shelf):
        rows = browse(shelf, "eksam", limit=50)
        kinds = {json.loads(r["meta"] or "{}").get("kind") for r in rows}
        assert kinds <= {"ulesanne"}

    def test_workbooks_are_revision_not_exam(self, shelf):
        """The one piece of official material that is homework."""
        assert by_id("vihikud").mode == "kordamine"


class TestModes:
    def test_every_section_declares_one(self):
        assert all(s.mode in MODES for s in SECTIONS)

    def test_all_three_have_something(self, shelf):
        for mode in MODES:
            found = sections(shelf, mode=mode)
            assert found, mode
            assert sum(s["items"] for s in found) > 0, mode

    def test_filtering_by_mode_is_a_partition(self, shelf):
        """Every section shows up under exactly one mode, so nothing is listed
        twice and nothing is missing from the navigation."""
        seen = [s["id"] for mode in MODES for s in sections(shelf, mode=mode)]
        assert sorted(seen) == sorted(s.id for s in SECTIONS)


class TestLanguage:
    def test_labels_are_estonian_and_notes_are_russian(self):
        """The rule from CLAUDE.md: the interface is exposure, the explanation
        is where comprehension has to win."""
        for section in SECTIONS:
            assert section.note, section.id
            assert any("Ѐ" <= ch <= "ӿ" for ch in section.note), (
                f"{section.id}: the note explains what a section is and must be "
                f"readable by a Russian speaker still learning Estonian"
            )

    def test_every_section_has_a_russian_name_too(self):
        for section in SECTIONS:
            assert section.ru and section.et
