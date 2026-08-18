"""One screen, five measures, and deliberately no overall percentage.

The temptation with a learning app is a single number. It is the wrong shape
here for a reason specific to this exam: the B1 tasemeeksam scores **four parts
separately** and fails you for a zero in any one of them. A learner at "68 %
overall" who has never done a listening task is not 68 % ready; they are going
to fail. An aggregate hides exactly the thing that decides the outcome.

So each section reports the measure that is honest for it:

| Section       | Measure                              | Why that one |
|---------------|--------------------------------------|--------------|
| Rada          | topics mastered / total              | mastery is binary per topic |
| Sõnavara      | known within each frequency band     | "1 200 of the top 2 000" means something; "12 % of Estonian" does not |
| Kordamine     | due now, and how much is scheduled   | the FSRS numbers already exist |
| Raamatukogu   | items opened, minutes                | exposure counts, and is not mastery |

Every connection is optional. A learner who has never opened the library should
see the library section reporting zero, not an app that refuses to render — and
a caller that has no vocabulary database should not get an exception for it.
"""

from __future__ import annotations

import sqlite3


def overview(
    progress: sqlite3.Connection | None = None,
    reviews: sqlite3.Connection | None = None,
    vocabulary: sqlite3.Connection | None = None,
    words: sqlite3.Connection | None = None,
    content: sqlite3.Connection | None = None,
) -> dict:
    """The five sections, each with its own measure. No aggregate, on purpose."""
    out: dict = {"sections": {}, "note": "no overall percentage — see the docstring"}

    if progress is not None:
        from .progress import report, resume

        rows = report(progress)
        out["sections"]["rada"] = {
            "et": "Rada",
            "mastered": sum(1 for r in rows if r.state == "mastered"),
            "total": len(rows),
            "available": sum(1 for r in rows if r.state in ("ready", "in progress")),
            "next": resume(progress),
        }

    if vocabulary is not None and words is not None:
        from .vocab import band_progress

        bands = band_progress(vocabulary, words)
        out["sections"]["sonavara"] = {
            "et": "Sõnavara",
            "bands": bands,
            "known_in_top": sum(b["known"] for b in bands),
            "top": bands[-1]["to"] if bands else 0,
        }

    if reviews is not None:
        from .review import stats

        info = stats(reviews)
        out["sections"]["kordamine"] = {
            "et": "Kordamine", "due": info["due"], "scheduled": info["total"],
        }

    if progress is not None:
        from .library import exposure

        out["sections"]["raamatukogu"] = {"et": "Raamatukogu", **exposure(progress)}

    if content is not None:
        from .library import sections as library_sections

        out["sections"]["raamatukogu"] = {
            **out["sections"].get("raamatukogu", {"et": "Raamatukogu"}),
            "available": {s["id"]: s["items"] for s in library_sections(content)},
        }

    return out
