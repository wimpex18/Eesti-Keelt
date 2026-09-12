"""Who made the material, under what licence, and what we did to it.

`sources.REGISTRY` has always been the licence ledger — every third party this
project touches, with the terms that govern it. Nothing served it. That is the
same defect as a writer with no caller, pointing the other way: a record kept
carefully and read by nobody, so nothing could contradict it and nobody it
credits could see the credit.

It has to be served because of what the licences actually say. EKI publish the
level vocabulary and the põhisõnavara sõnastik under CC BY 4.0, and their own
terms — on `arhiiv.eki.ee/litsents/`, repeated on `ekilex.ee` — are that the
material may be processed and presented in any way needed **provided the
reference to EKI is retained and the modifications are described**. This app
presents EKI's definitions on the word card and EKI's CEFR levels throughout
the drills. The obligation follows the text onto the screen; it is not
discharged by a paragraph in a repository the learner never opens.

Read from `REGISTRY` in code, never from the `sources` table: attribution has
to be answerable on a deployment with no corpus pushed, and the ledger is the
authority either way.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/sources")
def sources() -> dict:
    """The licence ledger, as the page needs it to render an attribution.

    Everything here is already public — a name, a licence, a link and a
    description of our own changes. Nothing about the learner, and no material.
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
