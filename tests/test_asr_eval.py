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


class TestComparingTwoEngines:
    """The question P5 exists to answer: does the other engine hear *this*
    learner better, or is it the clips?"""

    def _run(self, engine: str, rates: dict) -> dict:
        return {"engine": engine, "per_clip": sorted(rates.items())}

    def test_a_consistent_win_is_decisive(self):
        a = self._run("workers-ai", {"c1": 0.4, "c2": 0.5, "c3": 0.45, "c4": 0.5})
        b = self._run("taltech", {"c1": 0.1, "c2": 0.2, "c3": 0.15, "c4": 0.2})
        got = evaluation.compare(a, b)
        assert got["difference"] > 0 and got["decisive"]
        assert got["ci95"][0] > 0 and got["clips"] == 4

    def test_noise_is_not_a_result(self):
        """Half the clips better, half worse: the interval must straddle zero."""
        a = self._run("one", {f"c{i}": 0.3 for i in range(8)})
        b = self._run("two", {f"c{i}": 0.3 + (0.2 if i % 2 else -0.2)
                              for i in range(8)})
        assert not evaluation.compare(a, b)["decisive"]

    def test_runs_that_share_no_clips_say_so(self):
        got = evaluation.compare(self._run("a", {"x": 0.1}), self._run("b", {"y": 0.1}))
        assert got["difference"] is None and "nothing to compare" in got["note"]

    def test_it_says_the_numbers_describe_one_voice(self):
        got = evaluation.compare(self._run("a", {"c": 0.2}), self._run("b", {"c": 0.1}))
        assert "One voice" in got["note"]

    def test_the_cli_offers_two_engines(self):
        import argparse

        from eesti.cli import build

        parser = argparse.ArgumentParser()
        build.register(parser.add_subparsers())
        args = parser.parse_args(["eval", "--suite", "asr",
                                  "--engine", "workers-ai", "--engine", "whisper.cpp"])
        assert args.engine == ["workers-ai", "whisper.cpp"]

    def test_every_named_engine_exists_in_the_chain(self):
        from eesti.providers import asr

        assert set(asr.NAMES) == {name for name, _ in asr.engines(b"x")}
