"""A downloaded backup must replay, and checking it must not erase live work."""
import json
from pathlib import Path

import pytest

from eesti import config, evidence, recovery, vocab


def export_to(path):
    with evidence.connect() as log:
        path.write_text('\n'.join(json.dumps(e.to_dict()) for e in evidence.events(log)))


def test_private_export_replays_twice_without_touching_current_stores(tmp_path):
    with vocab.connect(config.VOCAB_DB) as words:
        vocab.set_status(words, 'raamat', 99)
    backup = tmp_path / 'backup.jsonl'
    export_to(backup)
    before = Path(config.EVENTS_DB).read_bytes()
    original = config.EVENTS_DB
    result = recovery.verify_export(backup)
    assert result['verified'] and result['projection_rows']['vocab.vocab_status'] == 1
    assert config.EVENTS_DB == original
    assert Path(config.EVENTS_DB).read_bytes() == before


def test_unsupported_event_is_not_a_successful_restore(tmp_path):
    evidence.record('future-unsupported', {})
    backup = tmp_path / 'backup.jsonl'
    export_to(backup)
    original = config.EVENTS_DB
    with pytest.raises(ValueError, match='cannot replay'):
        recovery.verify_export(backup)
    assert config.EVENTS_DB == original


def test_a_truncated_export_without_backfill_marker_is_refused(tmp_path):
    backup = tmp_path / 'backup.jsonl'
    backup.write_text('')
    with pytest.raises(ValueError, match='completeness'):
        recovery.verify_export(backup)


@pytest.mark.parametrize('problem', ['duplicate', 'version'])
def test_export_envelope_failures_do_not_touch_live_state(tmp_path, problem):
    with vocab.connect(config.VOCAB_DB) as words:
        vocab.set_status(words, 'raamat', 99)
    backup = tmp_path / 'backup.jsonl'
    export_to(backup)
    rows = [json.loads(line) for line in backup.read_text().splitlines()]
    if problem == 'duplicate':
        rows.append(rows[0])
    else:
        rows[0]['v'] = 999
    backup.write_text('\n'.join(json.dumps(row) for row in rows))
    before = Path(config.EVENTS_DB).read_bytes()
    with pytest.raises(ValueError):
        recovery.verify_export(backup)
    assert Path(config.EVENTS_DB).read_bytes() == before
