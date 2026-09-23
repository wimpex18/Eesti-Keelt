"""Verify a private JSONL export in isolated temporary databases, CLI only."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import config, evidence


def verify_export(path: Path) -> dict:
    """Exercise replay twice without touching the learner's working stores.

    This checks completeness markers and replayability, not authenticity. Keep
    exports private; the event payloads include writing and speech transcripts.
    No production restore or erasure is performed by this diagnostic.
    """
    incoming = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    if any(row.get("v", evidence.VERSION) not in (0, evidence.VERSION) for row in incoming):
        raise ValueError("unsupported event version in export")
    ids = [row["id"] for row in incoming]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate event ids in export")
    names = ("EVENTS_DB", "PROGRESS_DB", "REVIEW_DB", "VOCAB_DB", "NOTION_DB")
    before = {name: getattr(config, name) for name in names}
    with tempfile.TemporaryDirectory(prefix="eesti-recovery-") as folder:
        try:
            for name in names:
                setattr(config, name, str(Path(folder) / f"{name}.db"))
            with evidence.connect() as log:
                evidence.ingest(log, incoming)
                if not evidence.has_backfill(log):
                    raise ValueError("export has no backfill marker; completeness is unproven")
                evidence.rebuild(log, strict=True)
                first = _rows()
                evidence.rebuild(log, strict=True)
                if first != _rows():
                    raise ValueError("replaying the same export changed its projections")
                return {"verified": True, "events": len(incoming),
                        "projection_rows": {name: len(rows) for name, rows in first.items()},
                        "note": "Replay verified in temporary stores; no live state changed. "
                                "Caches, push subscriptions and audio are not in this export."}
        finally:
            for name, value in before.items():
                setattr(config, name, value)


def _rows() -> dict:
    stores = evidence.Stores()
    try:
        return {f"{db}.{table}": [tuple(row) for row in stores[db].execute(
                    f"SELECT * FROM {table} ORDER BY rowid")]
                for db, tables in evidence.PROJECTIONS.items() for table in tables}
    finally:
        stores.close()
