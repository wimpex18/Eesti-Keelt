"""The exam section in one request, and a verdict that names what to open.

Two changes with the same shape: replacing a count with a thing.

`exam_material` groups a level's official material by **what it is for** rather
than listing it flat. A sample performance, a workbook and a reading task are
three different activities that happen to share a level, and a single list
buries the one a learner who has never sat the exam most needs — the annotated
sample, which is the only artefact that shows what a pass looks like.

`readiness` used to say "13 official listening tasks". That tells you the shelf
is stocked. Naming one tells you what to do this evening, and only the second
changes what happens.
"""

from __future__ import annotations

import pytest

from eesti.library import exam_material, parts_touched
from eesti.progress import connect as progress_connect
from eesti.readiness import readiness
from eesti.sources import Item, add_items, connect, register


@pytest.fixture
def content(tmp_path):
    conn = connect(tmp_path / "content.db")
    register(conn)
    add_items(conn, [
        Item("harno", "kirjutamine", level="B1", title="B1 Ki2B isiklik-kiri",
             meta={"kind": "ulesanne", "url": "https://harno.ee/a.pdf"}),
        Item("harno", "kuulamine", level="B1", title="B1 Ku1 yl",
             audio_url="https://x/a.mp3",
             meta={"kind": "ulesanne", "url": "https://harno.ee/b.mp3"}),
        Item("harno", "eksam", level="B1", title="B1-taseme-sooritusnaidis",
             meta={"kind": "sooritusnaidis", "url": "https://harno.ee/s.pdf"}),
        Item("harno", "eksam", level="B1", title="B1 video",
             meta={"kind": "video", "url": "https://youtu.be/r68sY35ewtc"}),
        Item("harno", "eksam", level="B1", title="B1 konsultatsioon",
             meta={"kind": "konsultatsioon", "url": "https://harno.ee/k.pdf"}),
        Item("harno", "lugemine", level="A2", title="A2 Lu1",
             meta={"kind": "ulesanne"}),
    ])
    return conn


@pytest.fixture
def progress(tmp_path):
    return progress_connect(tmp_path / "p.db")


class TestExamMaterial:
    def test_the_sample_is_its_own_group(self, content):
        """It is the only thing here that shows what a pass looks like, and in
        a flat list it is one row among ninety-eight."""
        got = exam_material(content, "B1")
        assert [i["title"] for i in got["sooritusnaidis"]] == \
            ["B1-taseme-sooritusnaidis"]

    def test_tasks_are_split_by_exam_part(self, content):
        got = exam_material(content, "B1")
        assert set(got["ulesanded"]) == {"kirjutamine", "kuulamine"}

    def test_the_video_and_descriptor_are_separate_from_tasks(self, content):
        got = exam_material(content, "B1")
        assert got["video"] and "video" not in got["ulesanded"]

    def test_another_level_is_not_included(self, content):
        got = exam_material(content, "B1")
        titles = [t["title"] for part in got["ulesanded"].values() for t in part]
        assert "A2 Lu1" not in titles

    def test_links_travel_so_the_ui_can_send_you_there(self, content):
        """Nothing of HARNO's is stored, so a row without its URL is useless."""
        got = exam_material(content, "B1")
        assert got["sooritusnaidis"][0]["url"].startswith("https://")

    def test_a_level_with_nothing_returns_empty_groups(self, content):
        got = exam_material(content, "C1")
        assert got["ulesanded"] == {} and got["sooritusnaidis"] == []


class TestPartsTouched:
    def test_nothing_opened_is_no_contact(self, progress, content):
        assert parts_touched(progress, content) == {}

    def test_opening_a_listening_task_counts_for_listening(
        self, progress, content
    ):
        """"You have opened 14 texts" and "you have never opened a listening
        task" are different facts, and only the second is what the
        no-part-may-be-zero rule punishes."""
        from eesti.library import mark_seen

        row = content.execute(
            "SELECT id FROM items WHERE skill = 'kuulamine'").fetchone()
        mark_seen(progress, row["id"])
        assert parts_touched(progress, content).get("kuulamine") == 1

    def test_it_does_not_credit_the_wrong_part(self, progress, content):
        from eesti.library import mark_seen

        row = content.execute(
            "SELECT id FROM items WHERE skill = 'kuulamine'").fetchone()
        mark_seen(progress, row["id"])
        assert parts_touched(progress, content).get("lugemine") is None


class TestTheVerdictNamesSomething:
    def test_an_untouched_part_carries_a_task_to_open(self, progress, content):
        result = readiness("B1", progress=progress, content=content)
        untouched = [p for p in result.parts if p.touched is False]
        assert any(p.next_task for p in untouched)

    def test_the_reason_names_it_rather_than_counting(self, progress, content):
        result = readiness("B1", progress=progress, content=content)
        assert any("Начни с:" in r for r in result.reasons)

    def test_the_named_task_is_real_material(self, progress, content):
        result = readiness("B1", progress=progress, content=content)
        named = next(p.next_task for p in result.parts if p.next_task)
        titles = {r["title"] for r in content.execute("SELECT title FROM items")}
        assert named["title"] in titles

    def test_without_a_corpus_it_names_nothing_rather_than_guessing(
        self, progress
    ):
        result = readiness("B1", progress=progress)
        assert all(p.next_task is None for p in result.parts)
