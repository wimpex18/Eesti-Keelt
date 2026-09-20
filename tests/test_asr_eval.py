"""The speech-recognition eval: the boundary that has to exist before any engine
is swapped. No recordings, no number — never a number from nowhere.
"""

from __future__ import annotations

import pytest

from eesti.evals import asr as evaluation


class TestTheMeasures:
    @pytest.mark.parametrize("said,heard,rate", [
        ("Ma elan Tallinnas", "ma elan tallinnas", 0.0),      # case and stops
        ("Ma elan Tallinnas", "Ma elan Tartus", 1 / 3),
        ("Ma elan Tallinnas", "", 1.0),
    ])
    def test_word_error_rate_ignores_case_and_punctuation(self, said, heard, rate):
        assert evaluation.wer(said, heard) == pytest.approx(rate, abs=0.01)

    def test_character_error_rate_sees_a_one_letter_miss(self):
        assert 0 < evaluation.cer("kass", "kas") < evaluation.wer("kass", "kas")


class TestTheSet:
    def test_a_clip_needs_its_transcript(self, tmp_path):
        (tmp_path / "a.wav").write_bytes(b"RIFF")
        assert evaluation.clips(tmp_path) == []
        (tmp_path / "a.txt").write_text("Ma elan siin", encoding="utf-8")
        assert [c.name for c in evaluation.clips(tmp_path)] == ["a"]

    def test_a_planted_error_is_read_from_its_own_file(self, tmp_path):
        (tmp_path / "b.wav").write_bytes(b"RIFF")
        (tmp_path / "b.txt").write_text("Ma ostsin uus auto", encoding="utf-8")
        (tmp_path / "b.said").write_text("uus", encoding="utf-8")
        assert evaluation.clips(tmp_path)[0].planted == "uus"

    def test_no_recordings_is_reported_not_scored(self, tmp_path):
        got = evaluation.run(folder=tmp_path, verbose=False)
        assert got["valid"] is False and got["wer"] is None
        assert "record a few" in got["invalid_reason"]


class TestScoring:
    @pytest.fixture
    def heard(self, monkeypatch):
        def answer(text: str):
            from eesti.providers import asr

            monkeypatch.setattr(asr, "transcribe",
                                lambda *a, **k: asr.Transcript(text=text, engine="test"))
        return answer

    def _clip(self, tmp_path, said: str, planted: str = "") -> None:
        (tmp_path / "c.wav").write_bytes(b"RIFF")
        (tmp_path / "c.txt").write_text(said, encoding="utf-8")
        if planted:
            (tmp_path / "c.said").write_text(planted, encoding="utf-8")

    def test_a_perfect_transcript_scores_zero(self, tmp_path, heard):
        self._clip(tmp_path, "Ma elan Tallinnas")
        heard("Ma elan Tallinnas.")
        got = evaluation.run(folder=tmp_path, verbose=False)
        assert got["wer"] == 0.0 and got["valid"] and got["measured"] == 1

    def test_the_failure_that_flatters_the_learner_is_counted(self, tmp_path, heard):
        """The learner said `uus auto`; a recogniser that hands back `uue auto`
        hides the mistake, and a read-aloud score would call it right."""
        self._clip(tmp_path, "Ma ostsin uus auto", planted="uus")
        heard("Ma ostsin uue auto")
        got = evaluation.run(folder=tmp_path, verbose=False)
        assert got["planted_errors"] == 1 and got["false_accept"] == 1.0

    def test_a_planted_error_that_comes_back_is_not_counted(self, tmp_path, heard):
        self._clip(tmp_path, "Ma ostsin uus auto", planted="uus")
        heard("Ma ostsin uus auto")
        got = evaluation.run(folder=tmp_path, verbose=False)
        assert got["false_accept"] == 0.0

    def test_a_silent_engine_is_broken_not_perfect(self, tmp_path, heard):
        self._clip(tmp_path, "Ma elan Tallinnas")
        heard("")
        got = evaluation.run(folder=tmp_path, verbose=False)
        assert got["broken"] == 1 and got["measured"] == 0 and not got["valid"]
