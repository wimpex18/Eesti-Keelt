"""Indexing the exam board's own practice tasks.

This is the only material in the project written by the people who write the
real exam. Everything else is generated from a word list or harvested from a
radio archive; these 23 tasks are what the learner will actually be graded
against the shape of.

**Pointers, not copies.** The tasks are copyright Haridus- ja Noorteamet, they
live in an iframe on HARNO's site, and the scoring and immediate feedback that
make them worth doing only work there. A scraped copy would be dead text *and* a
redistribution risk; a link is strictly better on both counts. So nothing of
theirs is ever in this database, and these tests are where that is enforced
rather than promised.

Network tests are skipped when EIS is unreachable — a third party being down
must never fail this build, which is the rule the whole project runs on.
"""

from __future__ import annotations

import json

import pytest

from eesti.harvest.eis import LEVELS, Task, _skill_of, to_items


def a_task(**kw) -> Task:
    return Task(**{"id": "54955", "level": "A2", "skill": "lugemine",
                   "title": "Lugemine 3 (A2-tase, harjutusülesanne)", **kw})


class TestNothingOfTheirsIsStored:
    def test_the_body_is_empty(self):
        """The single most important assertion in this file."""
        assert to_items([a_task()])[0].body == ""

    def test_the_item_carries_a_link_instead(self):
        meta = to_items([a_task()])[0].meta
        assert meta["url"] == "https://eis.harno.ee/publicitems/54955"
        assert meta["external"] is True

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
    """These would have caught the plan's wrong assumption before it was built
    on: it said to filter by `aine=R`, which returns nothing at all."""

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
