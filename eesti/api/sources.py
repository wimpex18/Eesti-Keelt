"""Who made the material, under what licence, and what we did to it.

Serves `licences.REGISTRY` so the page can credit sources: CC BY 4.0 (EKI,
Ekilex) requires the reference to be kept and changes described wherever the
material is presented. Read from the registry in code, not the `sources` table,
so attribution works on a deployment with no corpus.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/sources")
def sources() -> dict:
    """The licence ledger as the page renders it: names, licences, links and our
    changes — all public.
    """
    from ..sources import REGISTRY

    return {
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "kind": s.kind,
                "licence": s.licence,
                "url": s.url,
                # Whether this may be served to anyone, or is owner-only and
                # lives behind Access. Rendered, because "personal study only"
                # is worth the learner knowing before they share a screenshot.
                "redistributable": s.redistributable,
                # Empty for everything we only link to, only count, or wrote
                # ourselves. Present exactly where a licence asks for it.
                "changes": s.changes,
                # Engines only: what the learner gives up by using the lane.
                "version": s.version,
                "quota": s.quota,
                # `none` | `text` | `audio`: what leaves the device. The fact a
                # learner is owed before they type or speak into it.
                "data_leaves": s.data_leaves,
                "retention": s.retention,
                "verified": s.verified,
            }
            for s in REGISTRY
        ],
        # The lanes, and what each one sees: rendered as its own list, because
        # "who hears my voice" is not a licence question.
        "engines": [
            {"id": s.id, "name": s.name, "version": s.version,
             "data_leaves": s.data_leaves, "retention": s.retention,
             "quota": s.quota, "verified": s.verified}
            for s in REGISTRY if s.kind == "engine"
        ],
        # The ones whose licence obliges this page to exist, so the page can
        # lead with them rather than making the reader hunt.
        "attribution_required": [s.id for s in REGISTRY if s.changes],
    }
