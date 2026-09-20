"""EKI's recordings: a human voice for the forms the drills teach, and for the
sentences dictation plays. Synthesis stays the fallback, never the first choice.
"""

from __future__ import annotations

import io
import wave

import pytest

from eesti import haaldus


def _wav(seconds: float = 0.4, rate: int = 48_000, value: int = 8000) -> bytes:
    """A mono 16-bit tone, the shape EKI's clips have."""
    import array

    frames = array.array("h", [value if i % 20 < 10 else -value
                               for i in range(int(rate * seconds))])
    out = io.BytesIO()
    with wave.open(out, "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(rate)
        clip.writeframes(frames.tobytes())
    return out.getvalue()


class TestTheIndexes:
    def test_the_tagged_pack_names_the_form(self, tmp_path):
        """`psv_00001.wav  SgN  aabits` — EKI's tag, then the form."""
        index = tmp_path / "soundpack.txt"
        index.write_text("psv_00001.wav\tSgN\taabits\n"
                         "psv_00002.wav\tSgP\t`aabitsat\n", encoding="utf-8")
        got = haaldus.index(index)
        assert [(e.form, e.tag) for e in got] == [("aabits", "sg n"),
                                                  ("aabitsat", "sg p")]

    def test_the_older_pack_names_the_lemma(self, tmp_path):
        index = tmp_path / "soundpack_alg.txt"
        index.write_text("psvalg_1000.mp3\t`aasta\taasta\n", encoding="utf-8")
        entry = haaldus.index(index)[0]
        assert entry.form == "aasta" and entry.lemma == "aasta" and entry.tag == ""

    @pytest.mark.parametrize("marked,plain", [
        ("`aadr`es's", "aadress"),      # third quantity and palatalisation
        ("`aasta+`aeg", "aastaaeg"),    # compound boundary
        ("koera", "koera"),
    ])
    def test_the_marks_come_off_the_lookup_key(self, marked, plain):
        assert haaldus.plain(marked) == plain

    def test_the_marks_are_kept_as_what_was_said(self, tmp_path):
        """`koera` and `k`oera` are different words; the spelling does not say
        so, which is why the mark is stored rather than dropped."""
        index = tmp_path / "i.txt"
        index.write_text("a.wav\tSgP\t`koera\n", encoding="utf-8")
        assert haaldus.index(index)[0].spoken == "`koera"


class TestCompression:
    def test_a_studio_clip_is_made_phone_sized(self):
        raw = _wav()
        small = haaldus.compress(raw)
        assert len(small) < len(raw) / 2
        with wave.open(io.BytesIO(small)) as clip:
            assert clip.getframerate() == haaldus.RATE
            assert clip.getnchannels() == 1

    def test_anything_it_cannot_read_is_left_alone(self):
        assert haaldus.compress(b"not a wav") == b"not a wav"

    def test_an_mp3_is_stored_as_it_is(self, tmp_path):
        (tmp_path / "a.mp3").write_bytes(b"ID3fake")
        (tmp_path / "i.txt").write_text("a.mp3\t`aasta\taasta\n", encoding="utf-8")
        conn = haaldus.connect(tmp_path / "audio.db")
        haaldus.build(tmp_path, tmp_path / "i.txt", conn)
        row = haaldus.spoken(conn, "aasta")
        assert row["mime"] == "audio/mpeg" and bytes(row["audio"]) == b"ID3fake"


class TestImporting:
    @pytest.fixture
    def pack(self, tmp_path):
        (tmp_path / "psv_1.wav").write_bytes(_wav())
        (tmp_path / "psv_2.wav").write_bytes(_wav())
        (tmp_path / "i.txt").write_text(
            "psv_1.wav\tSgN\tkoer\npsv_2.wav\tSgP\t`koera\n", encoding="utf-8")
        return tmp_path

    def test_it_imports_what_the_index_names(self, pack):
        conn = haaldus.connect(pack / "audio.db")
        got = haaldus.build(pack, pack / "i.txt", conn)
        assert got["added"] == 2 and haaldus.counts(conn)["forms"] == 2

    def test_it_keeps_only_what_the_app_teaches(self, pack):
        conn = haaldus.connect(pack / "audio.db")
        got = haaldus.build(pack, pack / "i.txt", conn, keep={"koer"})
        assert got["added"] == 1 and got["skipped"] == 1

    def test_a_missing_clip_is_counted_not_fatal(self, pack):
        (pack / "i.txt").write_text("gone.wav\tSgN\tkoer\n", encoding="utf-8")
        conn = haaldus.connect(pack / "audio.db")
        assert haaldus.build(pack, pack / "i.txt", conn)["missing"] == 1

    def test_the_asked_for_form_wins_over_another_of_the_same_word(self, pack):
        conn = haaldus.connect(pack / "audio.db")
        haaldus.build(pack, pack / "i.txt", conn)
        assert haaldus.spoken(conn, "koera", "sg p")["spoken"] == "`koera"
        assert haaldus.spoken(conn, "koer")["tag"] == "sg n"


class TestSentences:
    @pytest.fixture
    def corpus(self, tmp_path):
        (tmp_path / "lause00001.wav").write_bytes(_wav())
        (tmp_path / "lause00001.txt").write_text("Ma elan Tallinnas.", encoding="utf-8")
        (tmp_path / "lause00002.wav").write_bytes(_wav())
        (tmp_path / "lause00002.txt").write_text(" ".join(["sõna"] * 30),
                                                 encoding="utf-8")
        return tmp_path

    def test_it_imports_the_short_ones(self, corpus):
        conn = haaldus.connect(corpus / "audio.db")
        got = haaldus.build_sentences(corpus, conn, max_words=12)
        assert got["added"] == 1 and got["skipped"] == 1
        assert haaldus.spoken_sentences(conn) == ["Ma elan Tallinnas."]

    def test_a_sentence_is_found_by_exactly_what_was_read(self, corpus):
        conn = haaldus.connect(corpus / "audio.db")
        haaldus.build_sentences(corpus, conn)
        assert haaldus.said(conn, "Ma elan Tallinnas.") is not None
        assert haaldus.said(conn, "Ma elan tallinnas") is None
