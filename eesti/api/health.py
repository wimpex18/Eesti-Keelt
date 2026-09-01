"""What this process is, and what it can reach.

Three read-only reports: `/api/health` (is there a word list, is the origin
guarded, which build is answering), `/api/status` (where the learner stands)
and `/api/engines` (which providers are *configured* — deliberately not
whether they answer, which only a live call can establish).
"""

from __future__ import annotations

import os

from fastapi import APIRouter

from ..drills import TEMPLATES
from ..providers import tts
from .deps import (
    BOOT_ID,
    BUILD,
    content_available,
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
        # Distinguishes "the reading list is empty" from "the reading list is
        # broken" without going to the logs. The corpus is owner-only, so it is
        # supplied at runtime and its absence is a supported state.
        "library": content_available(),
        # Verifiable rather than assumed: on a deployment this must be true, and
        # if it is false the origin is answering the open internet.
        "origin_guarded": bool(os.environ.get("PROXY_TOKEN")),
        # Which build is answering. `null` from a source checkout; on a
        # deployment it is how you tell a stale image from a missing feature.
        "built": BUILD.get("built"),
        "revision": BUILD.get("revision") or None,
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
    """Which grammar engines this deployment can actually use.

    Configuration only — nothing here calls a provider, so it is free to poll
    and costs no quota.

    This exists because of a failure that was invisible from outside: the LLM
    key was set as a *Worker* secret, while the code that reads it runs in the
    Cloud Run container. Nothing errored. The checker quietly served offline
    mode — object-case candidates and typos, no explanations — and since only
    an explained correction offers a "log it" button, the whole Notion chain
    was inert too. All the exposure of holding a key and none of the benefit.

    `explains` is the question worth asking: an engine that cannot produce a
    Russian explanation cannot teach, whatever else it does.
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
        # Deliberately NOT called `explains`: each engine carries a field of
        # that name too, and a smoke check grepping the body for
        # `"explains":true` matched a per-engine one on a provider that was
        # not available — reporting the chain healthy while it was in offline
        # mode, and sending me looking for a traffic split that did not exist.
        # A summary field that shares a name with a per-item field is a trap
        # for every line-oriented reader.
        "can_explain": any(e["available"] and e["explains"] for e in engines),
        "fix": "deploy/set-llm-key.sh sets the key on the Cloud Run service",
    }
