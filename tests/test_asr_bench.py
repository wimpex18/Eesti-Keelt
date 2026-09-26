"""The ready-made speech benchmark: its planted errors point at the words the
harness scores, and its clips pass the harness's own seal check."""

from __future__ import annotations

import pytest

from eesti.evals import asr, asr_bench


@pytest.mark.parametrize("text, index, accepted", asr_bench.PLANTED)
def test_each_planted_index_names_the_wrong_word(text, index, accepted):
    words = asr._norm(text)
    assert 0 <= index < len(words)
    assert words[index] != asr._norm(accepted)[0]


def test_sealed_clips_are_accepted_by_the_harness(tmp_path):
    asr_bench._seal(tmp_path, "planted-00", b"RIFF-fake", "Ma ostsin uus auto.",
                    "tartunlp-tts", ["synthetic", "planted"], planted_index=2, accepted="uue")
    clips, excluded = asr.inventory(tmp_path)
    assert not excluded
    assert clips[0].annotation["provenance"] == "tartunlp-tts"
    assert clips[0].annotation["planted_index"] == 2


def test_voxtral_realtime_is_an_eval_engine_only():
    from eesti.providers import asr as providers

    assert "voxtral-rt" in providers.EVAL_NAMES
    assert "voxtral-rt" not in providers.NAMES, "never part of the production chain"
