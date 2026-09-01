"""The material: what is in it, what to read next, and opening one item.

Sections filter on skill *and* purpose (`meta.kind`), not skill alone —
`/api/modes` is the map. `/api/reading/next` ranks by comprehensibility for
this learner (the share of a text's lemmas they have met), never by a CEFR
level derived from vocabulary, which was measured and does not work.
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
    """The three things a learner is ever doing, and what is in each.

    One request instead of four: the client asks once and knows the whole
    shelf, which is what makes a three-way switch cheap enough to be the
    top-level navigation.
    """
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

    `section` exists because a skill is not a shelf. A section also carries the
    `kind` filters that keep an exam task out of the reading list and a
    consultation workbook out of the exam list, and asking by skill alone
    silently ignores them.

    It was added after finding that two of the seven sections — 82 items, the
    entire harvested listening archive and the 28 radio-course transcripts —
    could not be reached from the page at all. They were indexed, sectioned and
    covered by API tests; the page just never asked, because it could only ask
    by skill and it only ever asked for `lugemine`.

    `public_only` is deliberately NOT exposed as a parameter. This server is the
    single-user local one; the public deployment sets it, and making it a query
    parameter would let a caller ask for owner-only material by guessing.
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
        # How many there are, not how many came back. The page printed
        # `len(items)` as the library size, so a `limit` of 80 against 349
        # indexed texts read as "80 текстов" -- a page size in the clothes of a
        # total, and 269 texts that nothing could reach.
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
                # Official exam tasks are indexed, not copied: they are HARNO's
                # copyright and their scoring only works on their page. The UI
                # needs to send the learner there rather than open a reader on
                # an empty body.
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

    The reading research is specific about the mechanism: input works when it is
    understood, and understanding is gated by how much of the vocabulary the
    reader already has. A difficulty band cannot see that — it ranks texts
    against each other and says nothing about who is reading.

    So this sorts by known-word coverage and puts the **instructional** band
    first: texts the learner can follow with effort, which is where a text
    teaches rather than either boring or defeating them.

    It ranks; it does not filter. This docstring used to end "anything below
    the threshold is not offered at all", which the code has never done and
    must not: a learner with 411 known words scores about 13 % on native-ish
    news, so a threshold filter would hand them an empty list on the default
    view and no way to tell an empty library from a high bar. The band is
    reported honestly instead — `raske` says the text is above them without
    hiding it.
    """
    from ..difficulty import INSTRUCTIONAL, comprehensible, known_lemmas
    from ..library import browse
    from ..library import count as section_count

    known = known_lemmas(vocab_db())
    # The whole shelf, not a slice of it. This read `limit=120` against 349
    # indexed texts, so 229 of them could never be recommended however well
    # they fitted -- which defeats the one thing this endpoint exists to do,
    # since ranking a fixed arbitrary subset by *this learner's* vocabulary is
    # not ranking the library by it. Measured before changing: scoring all 349
    # takes 0.14 s against 0.05 s for 120. The cap was buying 90 milliseconds.
    conn = content_db()
    rows = browse(conn, section, limit=max(1, section_count(conn, section)))

    scored = []
    unmeasurable = 0
    for row in rows:
        if not (row["body"] or "").strip():
            continue
        profile = comprehensible(row["body"], known)
        if profile["total"] == 0:
            # No lemmas resolved. Either the text is empty, or the word
            # database is missing — `cli export` builds it and the image does
            # so at build time, but a source checkout may not have it. Counted
            # rather than silently dropped: every text failing this way
            # produced "0 teksti · 411 слов знакомо", a contradiction with no
            # explanation, which is the same shape as showing a zero that
            # means "not measured yet".
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
        # Distinguishes "the library is empty" from "nothing could be
        # measured", which look identical in a list of length zero.
        "unmeasurable": unmeasurable,
        "note": note,
    }


@router.get("/api/library/{item_id}")
def library_item(item_id: str, minutes: float = 0.0) -> dict:
    """One item with its full text, a vocabulary profile, and a record that it
    was opened.

    That last part was missing, and it was load-bearing. `library.open_item`
    exists to write two things — an exposure row and a vocabulary encounter per
    lemma — and this endpoint, the only way the web app ever opens a text, did
    a raw SELECT instead. So reading in the app fed nothing:

    - `readiness` reported "0 текстов" for Lugemine however much was read
    - `parts_touched` saw no contact, so every exam part stayed untouched
    - `vocab_status` stayed empty, so `/api/reading/next` could never rank by
      what the learner knows and said "слова ещё не отмечены" forever

    Third time this project has built a measurement without its writer. The
    recording is deliberately *encounter*, not knowledge: `record_encounter`
    bumps a met-count and never promotes a word to known, because a word
    skimmed past is not a word learned.
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
