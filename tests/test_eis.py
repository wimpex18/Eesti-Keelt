"""The exam board's own EIS practice tasks, read inside the app.

The task text and its recordings are fetched for private study (© Haridus- ja
Noorteamet) so a learner does not leave the app to read a task. **The key
stays at EIS**: the correct answers are nowhere in the page and nothing here
scores an EIS task — a task that was not fetched keeps its link, which is what
these tests pin. Network tests skip when EIS is unreachable.
"""

from __future__ import annotations

import json

import pytest

from eesti.harvest.eis import LEVELS, Task, _skill_of, to_items


def a_task(**kw) -> Task:
    return Task(**{"id": "54955", "level": "A2", "skill": "lugemine",
                   "title": "Lugemine 3 (A2-tase, harjutusülesanne)", **kw})


class TestWhatTheAppHolds:
    def test_a_task_that_was_not_fetched_links_out(self):
        """Rather than opening an empty reader."""
        item = to_items([a_task()])[0]
        assert item.body == ""
        assert item.meta["url"] == "https://eis.harno.ee/publicitems/54955"
        assert item.meta["external"] is True

    def test_a_fetched_task_carries_its_text_and_every_recording(self):
        clips = ["https://cdn.example/1.mp3", "https://cdn.example/2.mp3"]
        item = to_items([a_task()], {"54955": ("Loe lauseid ja vali vastus.", clips)})[0]
        assert item.body.startswith("Loe lauseid")
        assert item.meta["audio"] == clips
        # The reader plays them in order; the first is the item's own audio.
        assert item.audio_url == clips[0]
        assert item.meta["external"] is False

    def test_the_task_still_says_where_it_is_scored(self):
        item = to_items([a_task()], {"54955": ("Loe lauseid.", [])})[0]
        assert "EIS" in item.meta["note"]

    def test_the_frame_s_own_chrome_is_not_read_as_estonian(self):
        """"Kuulamiste arv: 0 /2" is the player's counter, not the task."""
        from eesti.harvest.eis import _CHROME

        assert _CHROME.sub(" ", "Kuulamiste arv: 0 /2 1. Mis täna ei sõida?").split() == [
            "1.", "Mis", "täna", "ei", "sõida?"]

    def test_the_licence_is_owner_only(self):
        """`eis` must never be servable to an anonymous visitor."""
        from eesti.sources import REGISTRY

        eis = next(s for s in REGISTRY if s.id == "eis")
        assert eis.redistributable is False


class TestClassification:
    @pytest.mark.parametrize("title,expected", [
        ("Lugemine 3 (A2-tase, harjutusülesanne)", "lugemine"),
        ("Kuulamine 1 (B1-tase, harjutusülesanne)", "kuulamine"),
    ])
    def test_the_exam_part_is_read_off_the_title(self, title, expected):
        assert _skill_of(title) == expected

    def test_anything_else_is_refused(self):
        """Filing an unknown task under a skill would put it in a list the
        learner is using to prepare for a specific exam part."""
        assert _skill_of("Matemaatika ülesanne 5") is None

    def test_the_levels_this_app_teaches_are_covered(self):
        assert "A2" in LEVELS and "B1" in LEVELS


class TestAgainstTheLiveCatalogue:
    """The search filters by `keeletase`; `aine=R` returns nothing."""

    @pytest.fixture(scope="class")
    @classmethod
    def live(cls):
        from eesti.harvest.eis import catalogue

        try:
            return catalogue(("A2", "B1"))
        except Exception as exc:  # noqa: BLE001 - a third party being down
            pytest.skip(f"EIS unreachable: {exc}")

    def test_both_target_levels_have_tasks(self, live):
        levels = {t.level for t in live}
        assert levels == {"A2", "B1"}

    def test_both_drillable_exam_parts_are_present(self, live):
        """Reading and listening are the two the exam board publishes; speaking
        and writing have no public tasks, which is why the app generates its
        own."""
        assert {t.skill for t in live} == {"lugemine", "kuulamine"}

    def test_the_a2_rehearsal_has_something_to_rehearse_with(self, live):
        """The optional A2 sitting is 07.11.2026, decided by 01.10.2026."""
        assert len([t for t in live if t.level == "A2"]) >= 5


class TestTheApiTellsTheUiToLinkOut:
    def test_a_pointer_is_flagged(self):
        from eesti.api.library import _pointer

        meta = json.dumps({"external": True, "url": "https://example.org/x"})
        assert _pointer(meta)["external"] is True

    def test_an_ordinary_text_is_not(self):
        from eesti.api.library import _pointer

        assert _pointer(json.dumps({"series": "keelekodi"})) == {}

    def test_broken_meta_does_not_take_the_library_down(self):
        from eesti.api.library import _pointer

        assert _pointer("{not json") == {}
