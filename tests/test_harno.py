"""The exam board's published task material — PDFs and listening audio.

Distinct from `eis.py`: that indexes the interactive self-scoring tasks, this
indexes the per-task files on the exam page, including the four writing types a
candidate is graded on and every listening track.

**© Haridus- ja Noorteamet, indexed and never downloaded.** Studying from these
is ordinary personal use; copying a hundred of someone else's exam files into a
database on a public deployment is not. `body` stays empty and this file is
where that is enforced.

Two bugs are pinned here, both found by running the thing rather than reading
it, and both silent:

- the link pattern required a URL to *end* in `.mp3`, and every audio track is
  served with `?version=1&...` — so all seventeen were missing and nothing said so
- classification looked only for whole words, and HARNO's B1 files use codes
  (`B1_Ki2B`, `B1_Lu1`, `B1_Ku3`, `B1_R2`), so every B1 file was dropped: the
  level this app exists for
"""

from __future__ import annotations

import pytest

from eesti.harvest.harno import _level_of, _skill_of, catalogue, to_items


class TestNothingIsCopied:
    def test_the_body_is_empty(self):
        from eesti.harvest.harno import Material

        item = to_items([Material(
            url="https://harno.ee/x/B1_Lu1_kuulutus.pdf", level="B1",
            skill="lugemine", title="B1 Lu1 kuulutus", kind="pdf")])[0]
        assert item.body == ""
        assert item.meta["external"] is True

    def test_audio_is_linked_not_fetched(self):
        from eesti.harvest.harno import Material

        item = to_items([Material(
            url="https://projektid.edu.ee/x/B1.mp3", level="B1",
            skill="kuulamine", title="B1 kuulamisülesanne nr 1", kind="mp3")])[0]
        assert item.audio_url == "https://projektid.edu.ee/x/B1.mp3"
        assert item.body == ""


class TestClassification:
    @pytest.mark.parametrize("name,level", [
        ("A2 Kirjutamine Esimene ülesanne2", "A2"),
        ("B1 Lu1 kuulutus", "B1"),
        ("B1 kuulamisülesanne nr 1", "B1"),
    ])
    def test_the_level_is_read_off_the_name(self, name, level):
        assert _level_of(name) == level

    @pytest.mark.parametrize("name,skill", [
        ("A2 Kirjutamine Esimene ülesanne2", "kirjutamine"),
        ("B1 kuulamisülesanne nr 1", "kuulamine"),
        # The codes. Matching only whole words dropped every one of these.
        ("B1 Ki2B isiklik-kiri", "kirjutamine"),
        ("B1 Lu1 kuulutus", "lugemine"),
        ("B1 Ku3 yl lünkülesanne", "kuulamine"),
        ("B1 R2 infovahetus", "raakimine"),
    ])
    def test_the_exam_part_is_read_off_the_name(self, name, skill):
        assert _skill_of(name) == skill

    def test_material_that_names_neither_is_skipped(self):
        """Framework documents and information sheets are real material but not
        a task for a part at a level; filing them as one would mislead."""
        assert _skill_of("euroopa keeleoppe raamdokument") is None
        assert _level_of("Teabeleht tasemeeksami sooritajale 2025") is None


class TestAgainstTheLivePage:
    @pytest.fixture(scope="class")
    @classmethod
    def live(cls):
        try:
            return catalogue()
        except Exception as exc:  # noqa: BLE001 - a third party being down
            pytest.skip(f"harno.ee unreachable: {exc}")

    def test_both_target_levels_are_covered(self, live):
        levels = {m.level for m in live}
        assert {"A2", "B1"} <= levels

    def test_the_listening_audio_is_found(self, live):
        """The bug that made this test exist: zero MP3s, silently."""
        assert [m for m in live if m.kind == "mp3"]

    def test_b1_material_is_found(self, live):
        """The other one: every B1 file dropped, silently."""
        assert [m for m in live if m.level == "B1"]

    def test_all_four_exam_parts_have_something(self, live):
        b1 = {m.skill for m in live if m.level == "B1"}
        assert b1 == {"kirjutamine", "kuulamine", "lugemine", "raakimine"}
