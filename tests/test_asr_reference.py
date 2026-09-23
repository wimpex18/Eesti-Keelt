"""Reference inference is local, verbatim, and never a production fallback."""
import io
from types import SimpleNamespace

from eesti.evals import asr_reference
from eesti.providers import asr


def test_reference_decodes_browser_bytes_without_an_answer_prompt(monkeypatch):
    calls = []

    class Model:
        def transcribe(self, audio, **options):
            assert isinstance(audio, io.BytesIO) and audio.read() == b'webm audio'
            calls.append(options)
            return iter([SimpleNamespace(text=' Ma ostsin'), SimpleNamespace(text=' uus auto')]), None

    monkeypatch.setenv('ASR_REFERENCE_MODEL', '/local/ct2')
    monkeypatch.setattr(asr_reference, '_load', lambda folder: (Model(), 'digest'))
    result = asr.transcribe_with('faster-whisper', b'webm audio', 'audio/webm')
    assert result.text == 'Ma ostsin uus auto'
    assert 'digest' in result.engine and not result.degraded
    assert calls == [{'language': 'et', 'task': 'transcribe', 'vad_filter': True,
                      'condition_on_previous_text': False, 'beam_size': 5, 'temperature': 0.0}]
    assert 'faster-whisper' not in dict(asr.engines(b'webm audio'))


def test_unconfigured_reference_does_not_download_a_model(monkeypatch):
    monkeypatch.delenv('ASR_REFERENCE_MODEL', raising=False)
    monkeypatch.setattr(asr_reference, '_load', lambda folder: (_ for _ in ()).throw(AssertionError()))
    assert asr.transcribe_with('faster-whisper', b'audio') is None


def test_reference_identity_changes_when_decoding_assets_change(tmp_path):
    for name in ('model.bin', 'config.json', 'tokenizer.json', 'preprocessor_config.json'):
        (tmp_path / name).write_bytes(b'original')
    original = asr_reference._fingerprint(tmp_path)
    (tmp_path / 'tokenizer.json').write_bytes(b'changed token ids')
    assert asr_reference._fingerprint(tmp_path) != original
