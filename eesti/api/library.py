"""The material: what is in it, what to read next, and opening one item.

Sections filter on skill *and* purpose (`meta.kind`); `/api/modes` is the map.
`/api/reading/next` ranks by comprehensibility for this learner, never by a
CEFR level derived from vocabulary.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ..lookup import annotate
from ..sources import count as content_count
from ..sources import query as content_query
from .deps import content_db, progress_db, vocab_db

router = APIRouter()

@router.get("/api/modes")
def modes() -> dict:
    """The three modes and what is in each, in one request."""
    from ..library import MODE_LABELS, MODES, sections as library_sections

    conn = content_db()
    return {
        "modes": [
            {
                "id": mode,
                "et": MODE_LABELS[mode][0],
                "ru": MODE_LABELS[mode][1],
                "sections": library_sections(conn, mode=mode),
            }
            for mode in MODES
        ]
    }


@router.get("/api/library")
def library(skill: str = "lugemine", section: str | None = None,
            level: str | None = None, band: str | None = None,
            limit: int = 60, offset: int = 0) -> dict:
    """Harvested study material, by skill or by section.

    Prefer `section`: it also applies the `kind` filters a skill alone ignores.
    `public_only` is not a parameter — a caller must not be able to request
    owner-only material by guessing.
    """
    conn = content_db()
    if section is not None:
        from ..library import browse
        from ..library import count as section_count

        try:
            rows = browse(conn, section=section, level=level, band=band,
                          limit=limit)
            total = section_count(conn, section=section, level=level, band=band)
        except KeyError as exc:
            raise HTTPException(
                status_code=404, detail=f"unknown section {section!r}") from exc
    else:
        rows = content_query(conn, skill=skill, level=level, band=band,
                             limit=limit, offset=offset)
        total = content_count(conn, skill=skill, level=level, band=band)
    return {
        # The section total, not the page length.
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r["id"],
                "title": r["title"],
                "level": r["level"],
                "band": r["band"],
                "source": r["source_name"],
                "licence": r["licence"],
                "audio_url": r["audio_url"],
                "words": len(( r["body"] or "").split()),
                # Official exam tasks are pointers (HARNO copyright, scored on their page); the UI
                # links out instead of opening an empty reader.
                **_pointer(r["meta"]),
            }
            for r in rows
        ]
    }


def _pointer(meta: str | None) -> dict:
    """`{"external": True, "url": ...}` for an indexed task, else `{}`."""
    try:
        data = json.loads(meta or "{}")
    except ValueError:
        return {}
    if not data.get("external"):
        return {}
    return {"external": True, "url": data.get("url"), "note": data.get("note")}


@router.get("/api/reading/next")
def reading_next(limit: int = 6, section: str = "lugemine") -> dict:
    """Texts to read next, ranked by how readable they are *for this learner*.

    Sorts by known-word coverage and puts the **instructional** band first — texts
    the learner can follow with effort. It ranks and never filters: a low coverage
    shows as `raske` rather than an empty list.
    """
    from ..difficulty import INSTRUCTIONAL, comprehensible, known_lemmas
    from ..library import browse
    from ..library import count as section_count

    known = known_lemmas(vocab_db())
    # Score the whole shelf, so any text can be recommended.
    conn = content_db()
    rows = browse(conn, section, limit=max(1, section_count(conn, section)))

    scored = []
    unmeasurable = 0
    for row in rows:
        if not (row["body"] or "").strip():
            continue
        profile = comprehensible(row["body"], known)
        if profile["total"] == 0:
            # No lemmas resolved (empty text, or no form index — run `cli export`): counted
            # as unmeasurable rather than silently dropped.
            unmeasurable += 1
            continue
        scored.append({
            "id": row["id"], "title": row["title"], "band": row["band"],
            "source": row["source_name"], "audio_url": row["audio_url"],
            **profile,
        })

    # Instructional first, then by coverage descending within each group. A
    # learner with no vocabulary recorded yet has no instructional band at all,
    # so the easiest available text leads instead of an empty list.
    scored.sort(key=lambda item: (
        0 if item["readability"] == "arendav" else 1, -item["coverage"]
    ))
    note = (
        "Отсортировано по доле знакомых слов. Первыми — тексты, которые "
        "читаются с усилием: именно там текст учит. Это словарное "
        "покрытие, а не оценка понимания."
    )
    if not scored and unmeasurable:
        note = (
            "Словарная база не собрана, поэтому покрытие посчитать нельзя — "
            "это не значит, что вы не знаете слов. Соберите её командой "
            "`cli export`; в образе она собирается при сборке."
        )
    return {
        "items": scored[:limit],
        "known_words": len(known),
        "threshold": INSTRUCTIONAL,
        # Distinguishes "the library is empty" from "nothing could be measured".
        "unmeasurable": unmeasurable,
        "note": note,
    }


@router.get("/api/library/{item_id}")
def library_item(item_id: str, minutes: float = 0.0) -> dict:
    """One item with its full text and vocabulary profile; opening records exposure
    and word encounters via `library.open_item`.

    Encounters are not knowledge: they bump a met-count and never mark a word known.
    """
    conn = content_db()
    row = conn.execute(
        """SELECT i.*, s.name AS source_name, s.licence
           FROM items i JOIN sources s ON s.id = i.source_id
           WHERE i.id = ?""",
        (item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Этот материал не найден — возможно, он ещё не загружен на сервер.")

    from ..library import open_item

    # Never let bookkeeping cost the learner the text they asked for.
    try:
        opened = open_item(conn, item_id, progress=progress_db(),
                           vocabulary=vocab_db(), minutes=minutes)
    except Exception:  # noqa: BLE001 - reading must work with no databases
        opened = {"lemmas": 0}

    return {
        "id": row["id"],
        "title": row["title"],
        "met_lemmas": opened.get("lemmas", 0),
        "body": row["body"],
        "level": row["level"],
        "source": row["source_name"],
        "licence": row["licence"],
        "audio_url": row["audio_url"],
        "band": row["band"],
        # The reader needs to know *what kind of thing* this is before it can
        # decide between a text, a player and an embed.
        "meta": json.loads(row["meta"] or "{}"),
        "url": json.loads(row["meta"] or "{}").get("url"),
        "profile": annotate(row["body"] or ""),
    }
