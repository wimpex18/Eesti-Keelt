"""Text to speech: the feature that turns any text into listening practice.

The plan asked for exactly this check — *"synthesise one sentence, assert WAV
≥100 KB and <5 s, confirm disk-cache hit on repeat"* — and it was never
written. TTS is what makes 397 harvested texts into listening material, and it
was the one core provider with no test at all.

The cache is not an optimisation here, it is the availability story. TartuNLP's
inference endpoints were **down** during the research that started this project
— four of them, at two universities, simultaneously. Audio that has been
synthesised once must keep playing when the synthesiser is unreachable, and
that is a property worth pinning rather than assuming.

Network tests are skipped when TartuNLP is unreachable. That is the same rule
the rest of the suite follows: a third party having a bad afternoon must never
fail this build.
"""

from __future__ import annotations

import time

import pytest

from eesti.providers import tts


class TestArgumentChecking:
    def test_empty_text_is_refused(self):
        """Synthesising nothing wastes a request and caches a silent file."""
        with pytest.raises(ValueError):
            tts.synthesize("   ")

    def test_an_unknown_voice_is_refused_with_the_list(self):
        """TartuNLP answers 200 with an error body for a bad speaker, which
        would have been cached as if it were audio."""
        with pytest.raises(ValueError) as caught:
            tts.synthesize("Tere", speaker="kellegi-teise-hääl")
        assert "mari" in str(caught.value)

    def test_the_learner_speed_is_slower_than_natural(self):
        """0.7 is the point: a B1 listener needs the words separated, and the
        exam's own recordings are slower than conversation."""
        assert tts.LEARNER_SPEED < 1.0


class TestCacheKey:
    def test_the_same_request_maps_to_the_same_file(self, tmp_path):
        a = tts.cache_path("Tere", "mari", 0.7, tmp_path)
        b = tts.cache_path("Tere", "mari", 0.7, tmp_path)
        assert a == b

    @pytest.mark.parametrize("kwargs", [
        {"text": "Tere hommikust"}, {"speaker": "tambet"}, {"speed": 1.0},
    ])
    def test_every_input_changes_the_key(self, tmp_path, kwargs):
        """Speed especially: the same sentence at 0.7 and 1.0 are different
        audio, and a key that ignored it would serve the wrong one."""
        base = dict(text="Tere", speaker="mari", speed=0.7)
        assert (tts.cache_path(**base, cache_dir=tmp_path)
                != tts.cache_path(**{**base, **kwargs}, cache_dir=tmp_path))

    def test_it_lands_under_the_given_directory(self, tmp_path):
        assert tmp_path in tts.cache_path("Tere", "mari", 0.7, tmp_path).parents


class TestAgainstTheLiveService:
    """The plan's numbers: 310 KB in 2.0 s, measured during research."""

    @pytest.fixture(scope="class")
    @classmethod
    def spoken(cls, tmp_path_factory):
        directory = tmp_path_factory.mktemp("tts")
        try:
            started = time.monotonic()
            path = tts.synthesize("Ma lugesin raamatu läbi.",
                                  cache_dir=directory, timeout=20)
            return path, time.monotonic() - started, directory
        except Exception as exc:  # noqa: BLE001 - a third party being down
            pytest.skip(f"TartuNLP unreachable: {exc}")

    def test_it_returns_real_audio(self, spoken):
        path, _, _ = spoken
        assert path.stat().st_size >= 100_000

    def test_it_is_a_wav(self, spoken):
        """Written straight to disk and served to an <audio> element, so a
        JSON error body would arrive as a file that never plays."""
        path, _, _ = spoken
        assert path.read_bytes()[:4] == b"RIFF"

    def test_it_is_fast_enough_to_wait_for(self, spoken):
        _, elapsed, _ = spoken
        assert elapsed < 5.0

    def test_the_second_call_never_touches_the_network(self, spoken):
        """The availability property, not a speed one: four research endpoints
        were down simultaneously when this project started, and audio already
        synthesised has to keep playing through that."""
        path, _, directory = spoken

        def explode(*args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError("cache miss: went to the network")

        import urllib.request

        original = urllib.request.urlopen
        urllib.request.urlopen = explode
        try:
            again = tts.synthesize("Ma lugesin raamatu läbi.",
                                   cache_dir=directory)
        finally:
            urllib.request.urlopen = original
        assert again == path
