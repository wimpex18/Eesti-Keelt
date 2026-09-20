"""The exam board's published task material — PDFs and listening audio.

Complements `eis.py`: per-task files on the exam page. HARNO publishes them for
candidates to practise with; this learner's copy is downloaded for private
study (`cli harvest-exam --download`), attributed to © Haridus- ja Noorteamet,
and read in the app. A task not downloaded still links out, and that fallback
is what these tests pin.

Pinned:

- audio URLs carry `?version=1&...`, so the pattern must not require `.mp3` at
  the end;
- B1 files use codes (`B1_Ki2B`, `B1_Lu1`, `B1_Ku3`, `B1_R2`), which classification
  must read;
- the level comes from the page's tab panel, not the filename.
"""

from __future__ import annotations

import pytest

from eesti.harvest.harno import _kind_of, _panels, _skill_of, catalogue, to_items


def _one_page_pdf(text: str) -> bytes:
    """The smallest PDF `pypdf` will extract `text` from."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, start))
    return bytes(out)


class TestWhatIsHeldLocally:
    """A downloaded task is read in the app; an absent one must still open at
    HARNO rather than showing a blank page."""

    def test_a_task_not_downloaded_links_out(self, tmp_path):
        from eesti.harvest.harno import Material

        item = to_items([Material(
            url="https://harno.ee/x/B1_Lu1_kuulutus.pdf", level="B1",
            skill="lugemine", title="B1 Lu1 kuulutus",
            kind="ulesanne", fmt="pdf")], root=tmp_path)[0]
        assert item.body == ""
        assert item.meta["external"] is True
        assert item.meta["file"] is None

    def test_a_downloaded_task_carries_its_text(self, tmp_path):
        """The PDF's own text, so the task can be read and answered in the app."""
        from eesti.harvest.harno import Material

        pdf = tmp_path / "B1" / "B1_Lu1_kuulutus.pdf"
        pdf.parent.mkdir()
        pdf.write_bytes(_one_page_pdf("Esimene ülesanne"))
        item = to_items([Material(
            url="https://harno.ee/x/B1_Lu1_kuulutus.pdf", level="B1",
            skill="lugemine", title="B1 Lu1 kuulutus",
            kind="ulesanne", fmt="pdf")], root=tmp_path)[0]
        assert "Esimene" in item.body
        assert item.meta["file"] == "B1/B1_Lu1_kuulutus.pdf"
        assert item.meta["external"] is False

    def test_audio_keeps_its_url(self, tmp_path):
        from eesti.harvest.harno import Material

        item = to_items([Material(
            url="https://projektid.edu.ee/x/B1.mp3", level="B1",
            skill="kuulamine", title="B1 kuulamisülesanne nr 1",
            kind="ulesanne", fmt="mp3")], root=tmp_path)[0]
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
        """Audio tracks with query strings are found."""
        assert [m for m in live if m.fmt in ("mp3", "wav")]

    def test_b1_material_is_found(self, live):
        """The other one: every B1 file dropped, silently."""
        assert [m for m in live if m.level == "B1"]

    def test_all_four_exam_parts_have_tasks_at_b1(self, live):
        b1 = {m.skill for m in live if m.level == "B1" and m.kind == "ulesanne"}
        assert b1 == {"kirjutamine", "kuulamine", "lugemine", "raakimine"}

    def test_the_four_b1_writing_tasks_are_all_there(self, live):
        """The four B1 writing task types (notice, questionnaire, set topic, letter) are
        classified.
        """
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
