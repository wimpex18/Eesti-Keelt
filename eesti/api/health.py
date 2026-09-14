"""What this process is, and what it can reach.

Three read-only reports: `/api/health` (is there a word list, is the origin
guarded, which build is answering), `/api/status` (where the learner stands)
and `/api/engines` (which providers are *configured* — deliberately not
whether they answer, which only a live call can establish).
"""

from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter

from ..drills import TEMPLATES
from ..providers import tts
from .deps import (
    BOOT_ID,
    BUILD,
    content_available,
    content_counts,
    content_db,
    db,
    progress_db,
    review_db,
    vocab_db,
)

router = APIRouter()

@router.get("/api/health")
def health() -> dict:
    conn = db()
    words = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    drillable = conn.execute(
        "SELECT COUNT(*) FROM object_cases WHERE distinct_=1"
    ).fetchone()[0]
    return {
        "words": words,
        "drillable_nouns": drillable,
        "rules": sorted({t.rule for t in TEMPLATES}),
        "voices": list(tts.VOICES),
        "boot": BOOT_ID,
        # Distinguishes an empty reading library (a supported state) from a broken one.
        "library": content_available(),
        # Corpus items and topic links as separate counts: a corpus without links serves
        # reading but gives every drill an empty `reading` list (`cli link-topics` fills
        # it).
        "corpus": content_counts(),
        # Verifiable rather than assumed: on a deployment this must be true, and
        # if it is false the origin is answering the open internet.
        "origin_guarded": bool(os.environ.get("PROXY_TOKEN")),
        # Which build is answering. `null` from a source checkout; on a
        # deployment it is how you tell a stale image from a missing feature.
        "built": BUILD.get("built"),
        "revision": BUILD.get("revision") or None,
        # Reference data imported at image build, as row counts: a database file existing
        # does not mean it holds data, and each import may fail without failing the build
        # (`docs/sources.md`), so the deployment reports which landed.
        "reference": _reference(conn),
    }


def _reference(conn) -> dict:
    from .. import ekidefs, evs, har, psv, rection

    def count(sql: str) -> int:
        try:
            return conn.execute(sql).fetchone()[0]
        except sqlite3.Error:
            return 0

    return {
        # EKK SÜ 64, via `cli rections` -- powers the rektsioon drill and the
        # &err-gov check in free writing.
        "rections": len(rection.load(conn)),
        # EKI's A1/A2/B1 vocabulary -- where a word's CEFR level is EKI's own
        # answer rather than an estimate off a 6.2 %-tagged list.
        "eki_levels": count("SELECT COUNT(*) FROM official_levels"),
        # EKI's learner dictionary -- the definition on a word card.
        "eki_definitions": psv.imported(conn),
        # EKI's Estonian-Russian dictionary -- the Russian on a word card.
        "eki_russian": evs.imported(conn),
        # Last fallbacks: education-term Russian, loanword definitions.
        "eki_terms": har.imported(conn),
        "eki_loanwords": ekidefs.imported(conn, "eki-vsl"),
        "eki_explanatory": ekidefs.imported(conn, "eki-ekss"),
    }


@router.get("/api/status")
def status() -> dict:
    """Every section with its own measure, and no overall percentage."""
    from ..overview import overview

    return overview(
        progress=progress_db(), reviews=review_db(), vocabulary=vocab_db(),
        words=db(), content=content_db(),
    )


@router.get("/api/engines")
def grammar_engines() -> dict:
    """Which grammar engines this deployment can use — configuration only.

    Calls no provider, so it is free to poll; it cannot tell whether a provider
    answers (the smoke check's deep mode does). `can_explain` matters because only
    an explaining engine teaches and offers "log it".
    """
    from ..providers.grammar import build_chain

    engines = [
        {"name": p.name, "available": p.available(),
         # Only an LLM writes the explanation; Vabamorf reports evidence and
         # TartuNLP answers in Estonian with no language parameter.
         "explains": p.name.startswith("llm:")}
        for p in build_chain()
    ]
    return {
        "engines": engines,
        # `can_explain`, not `explains`: every engine carries an `explains` field, and a
        # summary field sharing that name misleads line-oriented readers.
        "can_explain": any(e["available"] and e["explains"] for e in engines),
        "fix": "deploy/set-llm-key.sh sets the key on the Cloud Run service",
    }
