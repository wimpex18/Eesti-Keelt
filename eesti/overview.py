"""One screen, a measure per section, and deliberately no overall percentage.

The exam scores four parts separately and fails a zero in any, so an aggregate
hides what decides the outcome.

| Section       | Measure                              | Why that one |
|---------------|--------------------------------------|--------------|
| Rada          | topics mastered / total              | mastery is binary per topic |
| Sõnavara      | known within each frequency band     | "1 200 of the top 2 000" means something |
| Kordamine     | due now, and how much is scheduled   | FSRS numbers |
| Raamatukogu   | items opened, minutes                | exposure, not mastery |

Every connection is optional: a missing database reports zero, not an error.
"""

from __future__ import annotations

import sqlite3


def _gloss_line(vocabulary) -> dict:
    """Glossed-word counts, or nothing at all if the store is not there yet."""
    from . import gloss

    try:
        info = gloss.stats(vocabulary)
    except Exception:  # noqa: BLE001 - an older vocab.db predates the table
        return {}
    return {"glossed": info["with_russian"],
            "gloss_budget_left": info["budget_left"]}


def overview(
    progress: sqlite3.Connection | None = None,
    reviews: sqlite3.Connection | None = None,
    vocabulary: sqlite3.Connection | None = None,
    words: sqlite3.Connection | None = None,
    content: sqlite3.Connection | None = None,
) -> dict:
    """The five sections, each with its own measure. No aggregate, on purpose."""
    out: dict = {
        "sections": {},
        "note": "no overall percentage — see the docstring",
        # Russian, like every other explanation: this sentence is the reason
        # there is no single number, and it is worth nothing if unread.
        "caveat": (
            "Общего процента здесь нет: экзамен оценивает четыре части "
            "отдельно, и ноль в одной из них — это провал независимо от "
            "остальных. Сводная цифра спрятала бы именно то, что решает."
        ),
    }

    if progress is not None:
        from .progress import report, resume

        from .curriculum import by_id

        rows = report(progress)
        # Resolve the next topic's name here, so no caller prints a raw id.
        nxt = resume(progress)
        topic = by_id(nxt) if nxt else None
        out["sections"]["rada"] = {
            "et": "Rada",
            "mastered": sum(1 for r in rows if r.state == "mastered"),
            "total": len(rows),
            "available": sum(1 for r in rows if r.state in ("ready", "in progress")),
            "next": nxt,
            "next_et": topic.et if topic else None,
            "next_ru": topic.ru if topic else None,
        }

    if vocabulary is not None and words is not None:
        from .vocab import band_progress

        bands = band_progress(vocabulary, words)
        out["sections"]["sonavara"] = {
            "et": "Sõnavara",
            "bands": bands,
            "known_in_top": sum(b["known"] for b in bands),
            "top": bands[-1]["to"] if bands else 0,
            # How many words the learner can now see a translation for (`gloss.stats`).
            **_gloss_line(vocabulary),
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
