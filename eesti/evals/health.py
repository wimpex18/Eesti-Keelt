"""Bounded POST probes of the public GEC contract, separate from quality evals.

Uses the application's TLS, request builder and parser. Canned public sentences
only; never prints credentials or remote error bodies. No retries or breakers:
this is an explicit operator diagnostic, not a call in the learner's chain.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from ..providers.grammar import TartuNLPGrammar, why_failed

SENTENCES = (
    "Ma elan Tallinnas.",
    "Mul on kaks koer ja üks kass.",
    "Ma lugesin raamatut läbi.",
)


def probe(timeout: float = 5.0) -> dict:
    if not 0 < timeout <= 75:
        raise ValueError("timeout must be in (0, 75] seconds")
    provider = TartuNLPGrammar(timeout=timeout)
    rows = []
    for endpoint in provider.ENDPOINTS:
        for index, sentence in enumerate(SENTENCES):
            started = time.monotonic()
            row = {"endpoint": endpoint, "sample": index, "timeout": timeout}
            try:
                payload = provider._post(endpoint, sentence)
                parse = provider._from_v2 if endpoint.endswith('/v2') else provider._from_v1
                row.update(ok=True, status=200, corrections=len(parse(payload)))
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                row.update(ok=False, status=getattr(exc, "code", None),
                           failure=why_failed(exc))
            row["seconds"] = round(time.monotonic() - started, 3)
            rows.append(row)
    return {"checked_at": datetime.now(timezone.utc).isoformat(),
            "contract": {"language": "et", "text": "<canned sentence>"},
            "results": rows, "operational": all(r["ok"] for r in rows),
            "note": "Reachability/schema only; correction quality is not measured."}
