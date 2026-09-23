"""Text to speech via TartuNLP: synthesis, validation and the disk cache.

Audio synthesised once keeps playing from the cache when the service is
unreachable. Network tests skip when TartuNLP is unreachable.
"""

from __future__ import annotations

import struct
import time
from io import BytesIO
from pathlib import Path

import pytest

from eesti.providers import tts


class TestArgumentChecking:
    def test_empty_text_is_refused(self):
        """Empty text is not synthesised."""
        with pytest.raises(ValueError):
            tts.synthesize("   ")

    def test_an_unknown_voice_is_refused_with_the_list(self):
        """An error body returned with 200 (bad speaker) is not cached as audio."""
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
        base = {"text": "Tere", "speaker": "mari", "speed": 0.7}
        assert (tts.cache_path(**base, cache_dir=tmp_path)
                != tts.cache_path(**{**base, **kwargs}, cache_dir=tmp_path))

    def test_it_lands_under_the_given_directory(self, tmp_path):
        assert tmp_path in tts.cache_path("Tere", "mari", 0.7, tmp_path).parents


def wav_bytes(encoding=3):
    """Small RIFF fixture, including the live service's IEEE-float encoding."""
    bits = 32 if encoding == 3 else 16
    width = bits // 8
    fmt = struct.pack("<HHIIHH", encoding, 1, 22050, 22050 * width, width, bits)
    frames = bytes(width * 16)
    body = b"WAVEfmt " + struct.pack("<I", len(fmt)) + fmt
    body += b"data" + struct.pack("<I", len(frames)) + frames
    return b"RIFF" + struct.pack("<I", len(body)) + body


class TestAudioIntegrity:
    @pytest.mark.parametrize("encoding", [1, 3])
    def test_valid_audio_is_cached_without_conversion(self, monkeypatch, tmp_path, encoding):
        audio = wav_bytes(encoding)
        monkeypatch.setattr(tts.urllib.request, "urlopen", lambda *a, **k: BytesIO(audio))
        path = tts.synthesize("Tere.", cache_dir=tmp_path)
        assert path.read_bytes() == audio

        def unavailable(*a, **k):
            raise AssertionError("valid cached audio should remain available offline")

        monkeypatch.setattr(tts.urllib.request, "urlopen", unavailable)
        assert tts.synthesize("Tere.", cache_dir=tmp_path) == path

    @pytest.mark.parametrize("audio", [b'{"detail":"unavailable"}', b"", wav_bytes()[:-8]])
    def test_broken_audio_is_never_published(self, monkeypatch, tmp_path, audio):
        monkeypatch.setattr(tts.urllib.request, "urlopen", lambda *a, **k: BytesIO(audio))
        with pytest.raises(OSError, match="invalid WAV"):
            tts.synthesize("Tere.", cache_dir=tmp_path)
        assert not list(tmp_path.rglob("*.wav"))

    def test_poisoned_cache_is_repaired(self, monkeypatch, tmp_path):
        path = tts.cache_path("Tere.", "mari", 0.7, tmp_path)
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{"detail":"unavailable"}')
        audio = wav_bytes()
        monkeypatch.setattr(tts.urllib.request, "urlopen", lambda *a, **k: BytesIO(audio))
        assert tts.synthesize("Tere.", cache_dir=tmp_path).read_bytes() == audio

    def test_failed_publish_leaves_no_partial_cache(self, monkeypatch, tmp_path):
        audio = wav_bytes()
        monkeypatch.setattr(tts.urllib.request, "urlopen", lambda *a, **k: BytesIO(audio))

        def interrupted(source, destination):
            assert source.read_bytes() == audio
            assert not destination.exists()
            raise OSError("disk unavailable")

        monkeypatch.setattr(Path, "replace", interrupted)
        with pytest.raises(OSError, match="disk unavailable"):
            tts.synthesize("Tere.", cache_dir=tmp_path)
        assert not list(tmp_path.rglob("*.wav"))
        assert not list(tmp_path.rglob("*.tmp"))

    @pytest.mark.parametrize("speed", [0.1, 3, float("nan"), float("inf")])
    def test_bad_speed_is_rejected_before_network(self, speed):
        with pytest.raises(ValueError, match="speed"):
            tts.synthesize("Tere.", speed=speed)


class TestAgainstTheLiveService:
    """A sentence synthesises to a real WAV within a few seconds."""

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
        """A cached sentence plays without the network."""
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
