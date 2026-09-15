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
            }
            for s in REGISTRY
        ],
        # The ones whose licence obliges this page to exist, so the page can
        # lead with them rather than making the reader hunt.
        "attribution_required": [s.id for s in REGISTRY if s.changes],
    }
