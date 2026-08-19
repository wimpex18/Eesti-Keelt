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
- the level was read off the *filename*, which was structurally wrong: the page
  is four tab panels and inside a panel the files are named generically
  (`teade`, `Kuulamine 3`). Requiring a level in the name threw away 72 of 111
  files, including all four B1 writing task types and both speaking cards
"""

from __future__ import annotations

import pytest

from eesti.harvest.harno import _kind_of, _panels, _skill_of, catalogue, to_items


class TestNothingIsCopied:
    def test_the_body_is_empty(self):
        from eesti.harvest.harno import Material

        item = to_items([Material(
            url="https://harno.ee/x/B1_Lu1_kuulutus.pdf", level="B1",
            skill="lugemine", title="B1 Lu1 kuulutus",
            kind="ulesanne", fmt="pdf")])[0]
        assert item.body == ""
        assert item.meta["external"] is True

    def test_audio_is_linked_not_fetched(self):
        from eesti.harvest.harno import Material

        item = to_items([Material(
            url="https://projektid.edu.ee/x/B1.mp3", level="B1",
            skill="kuulamine", title="B1 kuulamisülesanne nr 1",
            kind="ulesanne", fmt="mp3")])[0]
        assert item.audio_url == "https://projektid.edu.ee/x/B1.mp3"
        assert item.body == ""


class TestClassification:
    def test_the_level_comes_from_the_page_structure(self):
        """Not the filename. `teade` is the B1 notice task and says so nowhere
        in its name — only the panel it sits in knows."""
        html = ('<div role="tabpanel" id="a2-tase"><a href="/x/teade.pdf">a</a>'
                '<div role="tabpanel" id="b1-tase"><a href="/y/jutt.pdf">b</a>')
        levels = [level for level, _ in _panels(html)]
        assert levels == ["A2", "B1"]

    @pytest.mark.parametrize("name,skill", [
        ("A2 Kirjutamine Esimene ülesanne2", "kirjutamine"),
        ("B1 kuulamisülesanne nr 1", "kuulamine"),
        # The codes. Matching only whole words dropped every one of these.
        ("B1 Ki2B isiklik-kiri", "kirjutamine"),
        ("B1 Lu1 kuulutus", "lugemine"),
        ("B1 Ku3 yl lünkülesanne", "kuulamine"),
        ("B1 R2 infovahetus", "raakimine"),
        # Named by what the candidate produces, never by the exam part. These
        # four *are* the B1 writing exam.
        ("teade", "kirjutamine"),
        ("jutt etteantud teemal", "kirjutamine"),
        ("küsimustiku täitmine", "kirjutamine"),
        ("B1 Ki2B isiklik-kiri", "kirjutamine"),
        ("Raakimine I teemakaardid", "raakimine"),
    ])
    def test_the_exam_part_is_read_off_the_name(self, name, skill):
        assert _skill_of(name) == skill

    def test_non_task_material_names_no_exam_part(self):
        assert _skill_of("euroopa keeleoppe raamdokument") is None
        assert _skill_of("Eesti-keele-tasemeeksamite-statistika-2019") is None


class TestWhatAFileIsFor:
    """Six kinds of thing share this page, and flattening them buries the
    useful ones — above all the annotated sample performance, which is the one
    artefact that shows a learner what a pass actually looks like."""

    @pytest.mark.parametrize("name,kind", [
        ("B1-taseme-sooritusnaidis", "sooritusnaidis"),
        ("B1 konsultatsioon 2021", "konsultatsioon"),
        ("Eesti keele tasemeeksamite statistika 2024", "statistika"),
        ("Teabeleht tasemeeksami sooritajale 2025", "teave"),
        ("Iseseisev-keelekasutaja", "kirjeldus"),
    ])
    def test_the_purpose_is_recognised(self, name, kind):
        assert _kind_of(name, _skill_of(name)) == kind

    def test_a_real_exam_part_outranks_a_weak_marker(self):
        """`B1 R2 infovahetus` is a speaking task. Matching "info" first filed
        it as an information sheet."""
        assert _kind_of("B1 R2 infovahetus", "raakimine") == "ulesanne"

    def test_a_sample_outranks_its_exam_part(self):
        """A sample answer for the writing task is a sample, not a task."""
        assert _kind_of("A2-taseme-sooritusnaidis", "kirjutamine") == "sooritusnaidis"


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
        assert [m for m in live if m.fmt in ("mp3", "wav")]

    def test_b1_material_is_found(self, live):
        """The other one: every B1 file dropped, silently."""
        assert [m for m in live if m.level == "B1"]

    def test_all_four_exam_parts_have_tasks_at_b1(self, live):
        b1 = {m.skill for m in live if m.level == "B1" and m.kind == "ulesanne"}
        assert b1 == {"kirjutamine", "kuulamine", "lugemine", "raakimine"}

    def test_the_four_b1_writing_tasks_are_all_there(self, live):
        """The ones the plan named: a notice, a questionnaire, a piece on a set
        topic, a personal letter. All four were being dropped."""
        titles = " ".join(
            m.title.casefold() for m in live
            if m.level == "B1" and m.skill == "kirjutamine"
        )
        for expected in ("teade", "küsimustiku", "jutt etteantud", "kiri"):
            assert expected in titles, expected

    def test_the_annotated_sample_performance_is_found(self, live):
        """Published with the authors' permission and commented — the only
        thing here that shows what a pass looks like."""
        assert [m for m in live if m.kind == "sooritusnaidis"]

    def test_the_intro_video_is_found(self, live):
        assert [m for m in live if m.kind == "video" and m.level == "B1"]

    def test_statistics_and_forms_belong_to_no_level(self, live):
        """They are named by year or purpose. Attributing them to a panel put
        eleven years of pass rates under C1."""
        for m in live:
            if m.kind in ("statistika", "vorm"):
                assert m.level == "", m.title
