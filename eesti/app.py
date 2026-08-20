"""Local single-user web app. No auth, no deployment, no cloud state.

Run with:  python -m eesti.cli serve
"""

from __future__ import annotations

import base64
import hmac
import json
import os
import secrets
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    Response,
)
from pydantic import BaseModel, Field

from .config import LEVELS
from .drills import TEMPLATES, generate, generate_verb_drills
from .grammar import REFERENCES, describe as describe_rule
from .lookup import annotate, lookup, principal_forms
from .providers import grammar
from .providers import tts
from . import mining, review
from .sources import connect as content_connect
from .sources import query as content_query
from .wordlist import connect

from .config import (  # noqa: E402  -- re-exported; tests and CLI read these
    NOTION_DB,
    PROGRESS_DB,
    REVIEW_DB,
    VOCAB_DB,
)


def content_db():
    """The harvested material, resolved when called.

    A module-level `CONTENT_DB = "data/content.db"` sat here and bypassed
    `config.CONTENT_DB` entirely, so redirecting the database had no effect on
    the web app — which is how a read-aloud endpoint passed locally and returned
    an empty list in CI. Same shape as the bug in `wordlist.connect`: a path
    frozen at import cannot be pointed anywhere else.
    """
    from . import config

    return content_connect(config.CONTENT_DB)


def content_available() -> bool:
    from . import config
    from .sources import available

    return available(config.CONTENT_DB)


def review_db():
    return review.connect(REVIEW_DB)


def progress_db():
    from . import progress

    return progress.connect(PROGRESS_DB)


def vocab_db():
    from . import vocab

    return vocab.connect(VOCAB_DB)


def gloss_db():
    """Word meanings, in `vocab.db` so the state snapshot carries them.

    Anywhere else and the store would evaporate on every Cloud Run cold start,
    which is the bug it exists to fix — see `eesti/gloss.py`.
    """
    from . import gloss

    return gloss.connect(VOCAB_DB)


# Generated items are not stored, so an answer arrives without the question. The
# client sends the item back with the answer and the server re-grades it, which
# keeps the API stateless — but it also means the client could send an item it
# was never given. That is fine for a single-user app behind Cloudflare Access
# and would not be for a multi-user one: the fix there is to sign the item or
# hold the session server-side, and this note exists so that is a decision
# rather than an oversight.

WEB = Path(__file__).parent / "web"

app = FastAPI(title="Eesti-Keelt", docs_url="/api/docs")


# Identifies this process. The Worker in front of the deployment reads it off
# every response: when it changes, the container it was talking to has been
# replaced and its disk is empty again, which is the cue to push the snapshot
# back in. Cloud Run scales to zero and gives no shutdown hook the Worker can
# see, so the boot id is how a restart is noticed at all.
BOOT_ID = secrets.token_hex(8)

PROXY_HEADER = "x-proxy-token"


@app.middleware("http")
async def _proxy_guard(request: Request, call_next):
    """Keep the origin from becoming a way around the front door.

    On Cloud Run the service is invoked unauthenticated -- that is what makes it
    free -- so its `run.app` URL answers the whole internet. Cloudflare Access
    sits in front of the *Worker*, not in front of that URL, so without this the
    Access policy would guard one of two doors and the harvested material it
    exists to protect would be a hostname guess away.

    `PROXY_TOKEN` is a secret only the Worker holds. Unset, the guard is off,
    because the default way to run this app is `cli serve` on a laptop and
    demanding a token there would be ceremony. `/api/health` reports which of
    the two it is, so "is the deployment actually closed?" has an answer you can
    check rather than assume.
    """
    expected = os.environ.get("PROXY_TOKEN")
    if expected and not hmac.compare_digest(
        request.headers.get(PROXY_HEADER, ""), expected
    ):
        return JSONResponse({"detail": "not authorised"}, status_code=403)
    response = await call_next(request)
    response.headers["x-boot-id"] = BOOT_ID
    return response


def db():
    return connect()


class CheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class DrillRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=50)
    levels: list[str] = Field(default_factory=lambda: list(LEVELS))
    rules: list[str] | None = None
    seed: int | None = None


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str = tts.DEFAULT_VOICE
    speed: float = Field(default=tts.LEARNER_SPEED, ge=0.5, le=2.0)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (WEB / "index.html").read_text(encoding="utf-8")


def _bind_breaker() -> None:
    """Point the provider breaker at the learner's database.

    Without this the breaker is per-process, and on Cloud Run — which scales to
    zero — that meant every cold container paid a dead provider's full timeout
    twice before stepping over it. `progress.db` rather than a file of its own
    so it rides the existing snapshot; the table is tiny and its lifetime is
    the same as the deployment's.
    """
    from .providers import breaker

    try:
        breaker.bind(progress_db())
    except Exception:  # noqa: BLE001 - an unbound breaker still works
        pass


_bind_breaker()


def build_info() -> dict:
    """When this image was built, and from what commit if the builder said.

    Read once and cached by the module-level call below: it is a file written
    at image build time and it cannot change while the process runs.

    Why it exists: a Python change was merged, the Worker redeployed, and the
    new endpoint was still absent from production — with no way to tell whether
    the container build had not run yet, had failed, or was never wired up.
    Running from a source checkout there is no file and no build, which is
    itself the honest answer.
    """
    import json
    from pathlib import Path

    try:
        return json.loads((Path("/app") / "BUILD_INFO").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"built": None, "revision": None}


BUILD = build_info()


@app.get("/api/health")
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


@app.post("/api/check")
def check(req: CheckRequest) -> dict:
    """Grammar check through the provider chain, plus what the text actually says.

    The back-translation is the addition, and it answers a question grammar
    checking structurally cannot. A checker tells you whether your Estonian is
    *well formed*. It cannot tell you whether it says what you meant — those
    are different failures, and for a learner the second is the more common and
    the more invisible one. Write `Ma käisin arsti juures` when you meant "I
    went to the doctor's" and every word is correct; write `Ma käisin arstiga`
    and it is still correct Estonian, and it now means you went *with* a doctor.
    No grammar chain flags that. Reading it back in Russian does.

    This is the one job an Estonian-trained NMT is better at than a general LLM,
    and it is free, keyless, and on the one TartuNLP endpoint that has never
    been down — measured again on 2026-08-20: translation answers in 1.0s while
    its grammar sibling on the same host returns 500 after 60.7s, unchanged
    since the first probe six months ago.

    Never blocking. If translation is unavailable the check returns exactly what
    it always did.
    """
    result = grammar.check(req.text).to_dict()

    from .providers.translate import translate

    back = translate(req.text, target="rus")
    result["back_translation"] = back.text if back else None
    return result


class QueueError(BaseModel):
    wrong: str = Field(min_length=1, max_length=2000)
    correct: str = Field(min_length=1, max_length=2000)
    why: str = Field(default="", max_length=2000)
    tag: str


@app.post("/api/notion/queue")
def notion_queue(row: QueueError) -> dict:
    """Hold a confirmed error for the Notion log. Queued, never sent.

    The `Vead` log is hand-curated, and its "three of a tag becomes this week's
    focus" rule is what identified `obj-case` as the priority at all. Appending
    every suspicion would turn a picked record into a dump and start that rule
    firing on noise -- so this endpoint only ever queues. `cli notion --push`
    is the one thing that writes, and it shows you the rows first.
    """
    from .notion import Row, connect, queue

    try:
        entry = Row(wrong=row.wrong, correct=row.correct, why=row.why, tag=row.tag)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    added = queue(connect(NOTION_DB), entry)
    return {"queued": added, "tag": entry.tag,
            "note": "Проверь через `cli notion`, отправь `cli notion --push`."}


@app.get("/api/notion/pending")
def notion_pending() -> dict:
    from .notion import connect, pending

    return {
        "items": [dict(r) for r in pending(connect(NOTION_DB))],
        # Whether pressing "send" can possibly work, said before it is pressed
        # rather than as a failure afterwards.
        "can_push": bool(os.environ.get("NOTION_TOKEN")),
    }


class NotionPush(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=50)


@app.post("/api/notion/push")
def notion_push(req: NotionPush) -> dict:
    """Send named rows to the `Vead` log. Nothing else, ever.

    This was missing, and its absence was quiet in the worst way. Corrections
    could be queued from the app but pushed only by `cli notion --push` — and
    the CLI does not exist on the deployment: the container is ephemeral and
    the learner is on a phone. So the queue filled and never drained, and the
    readiness verdict counted queued rows as writing evidence, which measured
    the queue rather than the log it is supposed to feed.

    It takes **ids**, not "push everything". The `Vead` log's worth is that it
    is curated — three rows sharing a tag become the focus of the week, and
    that rule is what identified `obj-case` in the first place. An endpoint
    that drained the queue wholesale would be the same mistake as appending
    every suspicion, one step later. The page shows the rows and sends the ones
    ticked.

    A row that fails to send stays queued. The queue is the record until Notion
    says it has one.
    """
    from .notion import Row, connect, mark_pushed, pending, push

    if not os.environ.get("NOTION_TOKEN"):
        raise HTTPException(
            status_code=503,
            detail="NOTION_TOKEN is not set on this service, so nothing can "
                   "be sent. The rows stay queued.",
        )

    conn = connect(NOTION_DB)
    by_id = {r["id"]: r for r in pending(conn)}
    sent, failed = [], []
    for row_id in req.ids:
        row = by_id.get(row_id)
        if row is None:
            # Already pushed, or never queued. Not an error worth failing the
            # whole request over, and worth naming so the page can drop it.
            failed.append({"id": row_id, "detail": "not queued"})
            continue
        ok, detail = push(Row(wrong=row["wrong"], correct=row["correct"],
                              why=row["why"], tag=row["tag"]))
        if ok:
            mark_pushed(conn, row_id)
            sent.append(row_id)
        else:
            failed.append({"id": row_id, "detail": detail})
    return {"sent": sent, "failed": failed,
            "remaining": len(pending(conn))}


@app.post("/api/drills")
def drills(req: DrillRequest) -> dict:
    """Generate object-case drills. Fully offline."""
    try:
        # verb-form is a different generator: it drills irregular stems rather
        # than object case, so it does not share the template pool.
        if req.rules == ["verb-form"]:
            items = generate_verb_drills(
                db(), count=req.count, levels=tuple(req.levels), seed=req.seed
            )
        else:
            items = generate(
                db(),
                count=req.count,
                levels=tuple(req.levels),
                rules=tuple(req.rules) if req.rules else None,
                seed=req.seed,
            )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"drills": [d.to_dict() for d in items]}


@app.get("/api/modes")
def modes() -> dict:
    """The three things a learner is ever doing, and what is in each.

    One request instead of four: the client asks once and knows the whole
    shelf, which is what makes a three-way switch cheap enough to be the
    top-level navigation.
    """
    from .library import MODE_LABELS, MODES, sections as library_sections

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


@app.get("/api/library")
def library(skill: str = "lugemine", section: str | None = None,
            level: str | None = None, band: str | None = None,
            limit: int = 60) -> dict:
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
        from .library import browse

        try:
            rows = browse(conn, section=section, level=level, band=band,
                          limit=limit)
        except KeyError as exc:
            raise HTTPException(
                status_code=404, detail=f"unknown section {section!r}") from exc
    else:
        rows = content_query(conn, skill=skill, level=level, band=band,
                             limit=limit)
    return {
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


@app.get("/api/reading/next")
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
    from .difficulty import INSTRUCTIONAL, comprehensible, known_lemmas
    from .library import browse

    known = known_lemmas(vocab_db())
    rows = browse(content_db(), section, limit=120)

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


@app.get("/api/library/{item_id}")
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
        raise HTTPException(status_code=404, detail="not found")

    from .library import open_item

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


def library_for_topic(topic: str, limit: int = 5) -> dict:
    """Reading that demonstrates one grammar topic, strongest first."""
    return {"topic": topic, "items": reading_for(topic, limit=limit)}


def grammar_rules() -> dict:
    """Every rule the app drills, linked to its section in the EKK handbook.

    Explanations point at the authority (Eesti keele käsiraamat) rather than
    restating it, so a learner who doubts a drill can check the source — and so
    we are not maintaining a parallel grammar that can drift.
    """
    return {"rules": [describe_rule(tag) for tag in REFERENCES]}


def grammar_rule(tag: str) -> dict:
    rule = describe_rule(tag)
    if not rule["known"]:
        raise HTTPException(status_code=404, detail=f"no reference for {tag!r}")
    return rule


def word_card(lemma: str) -> dict:
    """A word in its three principal forms, as a dictionary would cite it."""
    result = principal_forms(lemma)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=f"{lemma!r} not found")
    return result


@app.get("/api/lookup/{word}")
def lookup_word(word: str) -> dict:
    """Analyse one word: lemma, case, CEFR level, and its object-case pair."""
    return lookup(word)


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    target: str = "rus"


@app.post("/api/translate")
def translate_sentence(req: TranslateRequest) -> dict:
    """Translate one Estonian sentence, on request and never on its own.

    The endpoint the app has had configured since the first week and never
    called: `TARTUNLP_TRANSLATE` sat in `config.py` with no caller anywhere,
    which is the same defect as a measurement with no writer.

    It is worth having for the thing `gloss.py` cannot do. A word gloss says
    what `süütamine` means; it does not unpick `Neist 52 on kasvatatud Eestis`
    for someone who knows every word in it. Sentence-level help is a different
    tool and this is the free, Estonian-trained, keyless one.

    Deliberately a POST and deliberately not attached to anything that renders
    automatically. A reader handed Russian reads the Russian, and this app's
    whole reading design rests on working at the edge of what is understood
    rather than past it. The learner asks; nothing offers.
    """
    from .providers.translate import translate

    got = translate(req.text, target=req.target)
    if got is None:
        # A crutch that is briefly absent, not an error page.
        return {"ok": False, "text": None,
                "detail": "Перевод сейчас недоступен — попробуйте ещё раз."}
    return {"ok": True, "text": got.text, "target": got.target,
            "engine": got.engine}


@app.get("/api/enrich/{word}")
def enrich_word(word: str) -> dict:
    """The two things Vabamorf cannot say: what the word governs, and its type.

    `providers/sonapi.py` has always existed for exactly this — its own
    docstring says it "enriches a word the learner is actually looking at" —
    and nothing had ever called it. Sixty-two statements, zero coverage, no
    importer: the module-level version of an endpoint with no caller.

    Rection is the `rektsioon` error tag directly: which case a verb governs is
    a list, not a rule, and no amount of morphology derives it. The
    inflection type is the muuttüüp the Notion "Nomenid A–F" page already
    tracks.

    Deliberately a **second** request rather than part of `/api/lookup`. This
    one leaves the machine, and a word card must not wait on a third party or
    disappear when one is down. An empty object is the honest answer to "the
    lookup did not come back", and the page simply adds nothing.
    """
    from . import gloss
    from .providers import sonapi

    # Through the store, so a word is asked about once and then never again.
    # `sonapi`'s own cache is on the container's disk, which Cloud Run throws
    # away every time it scales to zero -- so the module that promises not to
    # hammer Sõnaveeb was re-requesting the same words every session.
    kept = gloss.remember(gloss_db(), word)
    if kept is None or not kept.found:
        return {"word": word, "found": False}
    return {
        "word": word,
        "found": True,
        "governs": [p.strip() for p in (kept.rection or "").split(",") if p.strip()],
        "inflection_type": kept.inflection_type,
        "definition": kept.definition,
        "examples": [],
        # The language policy says explanations are in Russian, and the API has
        # carried Russian glosses all along — under the per-meaning key the
        # module never read. Three at most: a word card is a reminder, not an
        # entry.
        "russian": list(kept.russian[:3]),
        # The dictionary this app deliberately does not rebuild. Sõnaveeb has
        # the full paradigm, audio, and every translation; sending the learner
        # there is the honest answer to "I want more than three fields", and it
        # costs one link rather than a scraper the maintainers asked us not to
        # write.
        "sonaveeb": sonapi.entry_url(kept.lemma),
    }


class ReviewAdd(BaseModel):
    kind: str
    lemma: str
    prompt: str
    answer: str
    tag: str | None = None
    distractor: str | None = None
    why_ru: str | None = None
    source: str = "drill"
    context: str | None = None


class ReviewGrade(BaseModel):
    id: str
    rating: str  # again | hard | good | easy


@app.get("/api/review")
def review_queue(limit: int = 20, kind: str | None = None) -> dict:
    """Items due for review, most overdue first."""
    items = review.due(review_db(), limit=limit, kind=kind)
    return {
        "items": [
            {
                "id": i.id, "kind": i.kind, "kind_et": _topic_name(i.kind),
                "lemma": i.lemma,
                "prompt": i.prompt, "answer": i.answer,
                "distractor": i.distractor, "why_ru": i.why_ru,
                "context": i.context, "reps": i.reps, "lapses": i.lapses,
            }
            for i in items
        ],
        # The queue is where the same words come back by design, so it is the
        # place a missing meaning compounds: an item can be answered correctly
        # from the form alone, review after review, without the word ever
        # meaning anything. Local store only -- twenty items would be twenty
        # live lookups.
        "glosses": _glosses_for([i.lemma for i in items]),
    }


@app.post("/api/review")
def review_add(req: ReviewAdd) -> dict:
    """Queue an item. Re-adding an existing one keeps its existing schedule."""
    item_id = review.add(
        review_db(), kind=req.kind, lemma=req.lemma, prompt=req.prompt,
        answer=req.answer, tag=req.tag, distractor=req.distractor,
        why_ru=req.why_ru, source=req.source, context=req.context,
    )
    return {"id": item_id}


@app.post("/api/review/grade")
def review_grade(req: ReviewGrade) -> dict:
    try:
        return review.grade(review_db(), req.id, req.rating)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown item") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class MineRequest(BaseModel):
    word: str
    context: str | None = None


class DrillFailed(BaseModel):
    lemma: str
    prompt: str
    answer: str
    rule: str
    distractor: str | None = None
    why_ru: str | None = None


@app.post("/api/mine")
def mine(req: MineRequest) -> dict:
    """Queue the grammar pattern behind a word met while reading.

    Refusals carry a reason, so the reader can explain why a word was not added
    rather than appearing to do nothing.
    """
    result = mining.from_reading(review_db(), req.word, context=req.context)
    return {"queued": result.queued, "reason": result.reason,
            "id": result.item_id, "kind": result.kind}


def review_failed(req: DrillFailed) -> dict:
    """Record a drill answered wrong: queue it and mark it missed in one step."""
    result = mining.from_failed_drill(
        review_db(), lemma=req.lemma, prompt=req.prompt, answer=req.answer,
        distractor=req.distractor, rule=req.rule, why_ru=req.why_ru,
    )
    return {"queued": result.queued, "id": result.item_id}


@app.get("/api/review/stats")
def review_stats() -> dict:
    return review.stats(review_db())


@app.post("/api/speak")
def speak(req: SpeakRequest) -> FileResponse:
    """Synthesize Estonian audio for arbitrary text — turns anything into listening practice."""
    try:
        path = tts.synthesize(req.text, speaker=req.voice, speed=req.speed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"TTS unavailable: {type(exc).__name__}"
        ) from exc
    return FileResponse(path, media_type="audio/wav", filename="eesti.wav")


# --------------------------------------------------------------------------
# The path: curriculum, practice, progress, placement, checkpoints
# --------------------------------------------------------------------------

class PracticeRequest(BaseModel):
    topic: str | None = None
    theme: str | None = None
    count: int = Field(default=10, ge=1, le=30)
    levels: list[str] = Field(default_factory=lambda: list(LEVELS))
    seed: int | None = None


class AnswerRequest(BaseModel):
    topic: str
    prompt: str
    answer: str
    given: str
    distractor: str = ""
    lemma: str = ""
    label: str = ""
    why_ru: str = ""


class _Answered:
    """A graded item reconstructed from the client, for recording only.

    `progress.record` and `handoff.queue_failed` need an object with these
    fields; they never regenerate the drill, so this is deliberately a plain
    carrier rather than a re-created generator item.
    """

    def __init__(self, req: "AnswerRequest") -> None:
        self.topic = req.topic
        self.prompt = req.prompt
        self.answer = req.answer
        self.distractor = req.distractor
        self.lemma = req.lemma
        self.label = req.label
        self.why_ru = req.why_ru

    def check(self, given: str) -> bool:
        return given.strip().casefold() == self.answer.casefold()


@app.get("/api/curriculum")
def curriculum_path() -> dict:
    """The whole syllabus in study order, with where the learner stands on each."""
    from .progress import report, resume

    progress = progress_db()
    rows = report(progress)
    # `blocked_by` holds topic ids, and the page printed them straight onto the
    # screen: "astmevaheldus <- gen-stem". `gen-stem` is a database key; the
    # thing the learner has to go and study is called `omastava tüvi`, and the
    # whole point of an Estonian label here is that the term is what gets
    # learned. Eleven rows read that way.
    #
    # Resolved here rather than in the page, because this is the third time the
    # same bug has been fixed in a different place -- `kusisonad` on this very
    # panel, then `obj-case` in the review queue. A page that has to know how to
    # turn ids into names will eventually meet an id nobody taught it about.
    names = {r.topic: r.et for r in rows}
    return {
        "resume": resume(progress),
        "mastered": sum(1 for r in rows if r.state == "mastered"),
        "total": len(rows),
        "topics": [
            {
                "id": r.topic, "level": r.level, "et": r.et, "state": r.state,
                "attempts": r.attempts, "accuracy": r.accuracy,
                # Ids kept as well: the page needs them to link, and a caller
                # that wants to match on identity must not have to reverse a
                # display string to get it back.
                "blocked_by": [names.get(b, b) for b in r.blocked_by],
                "blocked_by_ids": list(r.blocked_by),
            }
            for r in rows
        ],
    }


@app.get("/api/themes")
def themes_list() -> dict:
    from .themes import coverage

    return {"themes": [{"id": k, **v} for k, v in coverage(db()).items()]}


@app.post("/api/practice")
def practice_items(req: PracticeRequest) -> dict:
    """Items for one topic — the topic you are on, unless you name another."""
    from .curriculum import by_id
    from .practice import items_for
    from .progress import resume

    topic = req.topic or resume(progress_db())
    if topic is None:
        return {"topic": None, "items": [], "detail": "nothing unlocked to practise"}

    try:
        items = items_for(
            topic, count=req.count, levels=tuple(req.levels), seed=req.seed,
            theme=req.theme,
        )
    except (ValueError, RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    meta = by_id(topic)
    # An empty list is not self-explanatory, and the page can only print what
    # it is given: without a reason it showed a bare "midagi ei tulnud".
    #
    # The generators that draw on the harvested corpus produce nothing when the
    # corpus has not been supplied, which is a supported state and a completely
    # different problem from a generator that is broken. Say which it is, and
    # in Russian, because it is an instruction the learner has to act on.
    detail = None
    if not items:
        needs_corpus = meta.generator in ("corpus_cloze", "ekk_rection", "wordorder")
        detail = (
            "Для этой темы нужен текстовый корпус, а он ещё не загружен на "
            "сервер — задания появятся после `deploy/push-content.sh`."
            if needs_corpus else
            f"Генератор «{meta.generator}» ничего не вернул для этой темы."
        )

    return {
        "topic": topic,
        "level": meta.level,
        "et": meta.et,
        "ru": meta.ru,
        "detail": detail,
        "reference": describe_rule(meta.tag) if meta.tag else None,
        "items": [i.to_dict() for i in items],
        # What the words in this set mean, from the local store only.
        #
        # A B1 object-case set comes back on lemmas like `etendus`, `luuletus`
        # and `rahakott`. A learner can inflect those correctly without knowing
        # one of them, and then has practised morphology on a token -- which is
        # half of what the exercise looks like it is teaching.
        #
        # Local reads only: a live lookup per item would be the batch request
        # `sonapi` refuses to have a helper for, and would make a practice set
        # wait on a third party. Words not yet stored are simply not glossed,
        # and get filled one at a time as each item is answered.
        "glosses": _glosses_for([i.lemma for i in items]),
        # Something to read that is *about* this contrast, not merely at this
        # level. This is the join that makes practice and the reading library
        # one tool: a drill teaches the rule, a text shows it being used.
        "reading": reading_for(topic),
    }


def _topic_name(kind: str) -> str:
    """A curriculum id turned into words a learner recognises.

    `obj-case` and `kusisonad` are database keys. The path panel already
    resolves them -- `overview.py` does it for exactly this reason -- and the
    review queue was still printing the raw id beside every card.
    """
    from .curriculum import by_id

    try:
        return by_id(kind).et
    except KeyError:
        # `vocab`, and anything queued before a topic was renamed. The raw
        # string is a worse label than a real name and a better one than blank.
        return kind


def _glosses_for(lemmas: list[str]) -> dict[str, list[str]]:
    """Russian for whatever is already known locally. Never fetches."""
    from . import gloss

    try:
        found = gloss.stored_many(gloss_db(), lemmas)
    except sqlite3.Error:
        return {}
    return {k: list(g.russian) for k, g in found.items() if g.russian}


def reading_for(topic: str, limit: int = 3) -> list[dict]:
    """Texts that demonstrate a topic, or nothing if the corpus is unharvested."""
    from .library import related

    try:
        return related(content_db(), topic, limit=limit)
    except sqlite3.Error:
        # An older content.db predates the link table. An empty reading list is
        # the right degradation -- the practice items are the lesson.
        return []


@app.post("/api/practice/answer")
def practice_answer(req: AnswerRequest) -> dict:
    """Grade one answer, record it, and queue it for review if it was missed."""
    from .handoff import queue_failed
    from .progress import (MASTERY_CORRECT, MASTERY_WINDOW, accuracy,
                           is_mastered, record)

    item = _Answered(req)
    correct = item.check(req.given)
    progress = progress_db()
    was_mastered = is_mastered(progress, req.topic)
    record(progress, item, correct, answer=req.given)

    if not correct:
        try:
            queue_failed(review_db(), item)
        except Exception:  # noqa: BLE001 - review is enrichment, never a blocker
            pass

    mastered_now = is_mastered(progress, req.topic)
    if mastered_now and not was_mastered:
        from .handoff import seed_mastered

        seed_mastered(review_db(), req.topic)

    # One lookup, for the one word the learner just spent thought on. This is
    # the "word in front of the learner" case `sonapi` exists for, and it is
    # also the right moment pedagogically: the meaning lands straight after the
    # struggle with the form, not before it as a hint.
    meaning: list[str] = []
    if req.lemma:
        from . import gloss

        try:
            kept = gloss.remember(gloss_db(), req.lemma)
            meaning = list(kept.russian) if kept else []
        except Exception:  # noqa: BLE001 - a gloss is never worth failing a grade
            meaning = []

    return {
        "correct": correct,
        "answer": req.answer,
        "why_ru": req.why_ru,
        "russian": meaning,
        "accuracy": accuracy(progress, req.topic),
        "mastered": mastered_now,
        "just_mastered": mastered_now and not was_mastered,
        "gate": f"{MASTERY_CORRECT}/{MASTERY_WINDOW}",
    }


@app.get("/api/exam/{level}")
def exam(level: str) -> dict:
    """The whole exam section for one level, in one request."""
    from .library import exam_material

    if level not in LEVELS + ("B2", "C1"):
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    return exam_material(content_db(), level)


@app.get("/api/readiness/{level}")
def exam_readiness(level: str) -> dict:
    """Evidence for and against sitting a level, with the reasons named.

    Not a prediction. The pass rule is 60% overall *and* no part at zero, so
    this reports every part separately — an aggregate would hide the untouched
    part that is the actual risk.
    """
    from .readiness import readiness

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    from .notion import connect as notion_connect

    return readiness(
        level, progress=progress_db(), vocabulary=vocab_db(), words=db(),
        content=content_db(), notion=notion_connect(NOTION_DB),
    ).to_dict()


@app.get("/api/checkpoint/{level}")
def checkpoint_items(level: str, count: int = 15, seed: int | None = None) -> dict:
    """A mixed set across a whole level — interleaved by construction."""
    from .checkpoint import PASS_MARK, build, ready, topics_at

    if level not in LEVELS:
        raise HTTPException(status_code=404, detail=f"unknown level {level!r}")
    items = build(level, count=count, seed=seed)
    return {
        "level": level,
        "ready": ready(progress_db(), level),
        "pass_mark": PASS_MARK,
        "topics": topics_at(level),
        "items": [i.to_dict() for i in items],
        # What the words in this set mean, from the local store only.
        #
        # A B1 object-case set comes back on lemmas like `etendus`, `luuletus`
        # and `rahakott`. A learner can inflect those correctly without knowing
        # one of them, and then has practised morphology on a token -- which is
        # half of what the exercise looks like it is teaching.
        #
        # Local reads only: a live lookup per item would be the batch request
        # `sonapi` refuses to have a helper for, and would make a practice set
        # wait on a third party. Words not yet stored are simply not glossed,
        # and get filled one at a time as each item is answered.
        "glosses": _glosses_for([i.lemma for i in items]),
    }


@app.get("/api/status")
def status() -> dict:
    """Every section with its own measure, and no overall percentage."""
    from .overview import overview

    return overview(
        progress=progress_db(), reviews=review_db(), vocabulary=vocab_db(),
        words=db(), content=content_db(),
    )


class KnownWords(BaseModel):
    lemmas: list[str] = Field(min_length=1, max_length=200)
    long_known: bool = False


def vocab_bands() -> dict:
    from .vocab import band_progress, summary

    vocabulary = vocab_db()
    return {"bands": band_progress(vocabulary, db()), **summary(vocabulary)}


@app.post("/api/vocab/known")
def vocab_known(req: KnownWords) -> dict:
    """Marking a word known is an explicit act — never inferred from reading."""
    from .vocab import KNOWN, WELL_KNOWN, set_status

    vocabulary = vocab_db()
    status_ = WELL_KNOWN if req.long_known else KNOWN
    for lemma in req.lemmas:
        set_status(vocabulary, lemma.strip().lower(), status_)
    return {"marked": len(req.lemmas)}


@app.get("/api/speaking")
def speaking_bank(kind: str | None = None) -> dict:
    """Questions in the exam's shape. No scoring — see `eesti/speaking.py`."""
    from .speaking import KINDS, bank

    return {
        "kinds": KINDS,
        "questions": [
            {"topic": q.topic, "question": q.question, "hint_ru": q.hint_ru,
             "kind": q.kind}
            for q in bank(kind)
        ],
    }


# --------------------------------------------------------------------------
# Installable on a phone: manifest and icons
# --------------------------------------------------------------------------

ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#1c6b52"/>'
    '<text x="32" y="44" font-family="ui-sans-serif,system-ui,sans-serif" '
    'font-size="34" font-weight="700" fill="#fff" text-anchor="middle">ä</text>'
    "</svg>"
)


@app.get("/vendor/{name}")
def vendor(name: str) -> FileResponse:
    """Third-party browser libraries, served from here rather than a CDN.

    One of them is load-bearing: 44 of the 91 audio items are HLS streams,
    which Safari plays natively and Chrome and Firefox do not. Without hls.js
    half the listening library is silently silent on a laptop.

    Served locally because the rest of this app already refuses to depend on
    someone else's uptime for a lesson, and a CDN is exactly that dependency in
    a smaller package.
    """
    path = (WEB / "vendor" / name).resolve()
    # Path traversal: `name` comes from the URL.
    if path.parent != (WEB / "vendor").resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type="application/javascript")


@app.get("/icon.svg")
def icon_svg() -> Response:
    return Response(ICON_SVG, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.get("/icon.png")
def icon_png() -> Response:
    """iOS ignores SVG for the home-screen icon, so serve the SVG's bytes under
    a .png name only if a real PNG exists; otherwise fall back to the SVG.

    Kept deliberately simple: adding a raster toolchain to draw one letter would
    be a dependency for a favicon.
    """
    png = WEB / "icon.png"
    if png.exists():
        return FileResponse(png, media_type="image/png")
    return Response(ICON_SVG, media_type="image/svg+xml")


@app.get("/manifest.webmanifest")
def manifest() -> Response:
    """Enough for "Add to Home Screen" to produce an app-like window."""
    return Response(
        json.dumps({
            "name": "Eesti keel",
            "short_name": "Eesti keel",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f7f7f5",
            "theme_color": "#1c6b52",
            "lang": "et",
            "icons": [
                {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml",
                 "purpose": "any"},
            ],
        }),
        media_type="application/manifest+json",
    )


@app.get("/api/engines")
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
    from .providers.grammar import build_chain

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


class DictationAnswer(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    typed: str = Field(default="", max_length=800)


@app.get("/api/dictation/next")
def dictation_next(count: int = 1, seed: int | None = None) -> dict:
    """Sentences to write down, easiest-first for this learner.

    The corpus is owner-only and supplied at runtime, so an empty library is a
    supported state and answers 200 with an empty list — the same contract the
    reading views use. A 404 here would read as a broken feature.
    """
    from .dictation import CAVEAT, MAX_WORDS, MIN_WORDS, choose

    try:
        content = content_db()
    except Exception:  # noqa: BLE001 - no corpus is a state, not an error
        content = None
    passages = choose(
        content, vocabulary=vocab_db(), count=max(1, min(count, 10)), seed=seed,
    ) if content is not None else []
    return {
        "passages": [p.to_dict() for p in passages],
        "words": [MIN_WORDS, MAX_WORDS],
        "caveat": CAVEAT,
        "note": ("Kuula ja kirjuta üles. Kuulata võib nii mitu korda kui vaja."
                 if passages else
                 "Tekstikogu on tühi — lisa materjal, siis tulevad ka diktaadid."),
    }


@app.post("/api/dictation/answer")
def dictation_answer(req: DictationAnswer) -> dict:
    """Grade a submission, and write it down.

    Graded server-side for the same reason every other answer is: a page can
    be edited, and a score the browser computed measures nothing. Recorded in
    the same call, because a listening exercise whose result nothing stores is
    how the verdict came to report this part as untouched no matter how much
    had been played.
    """
    from .dictation import Passage, grade, key_of, record

    passage = Passage(req.text, key_of(req.text), len(req.text.split()))
    result = grade(passage, req.typed)
    record(progress_db(), result)
    return result.to_dict()


def dictation_stats() -> dict:
    from .dictation import stats

    return stats(progress_db())


@app.get("/api/asr")
def asr_available() -> dict:
    """Which speech engines this deployment can use — shown in the UI as-is."""
    from .providers import asr

    return asr.available()


@app.post("/api/transcribe")
async def transcribe(request: Request) -> dict:
    """Transcribe a recording. Optional everywhere: no engine is still a 200.

    **Where the voice goes, stated plainly.** This docstring used to say the
    local engine was preferred and nothing left the machine. That stopped being
    true when recognition moved to the Worker's Workers AI binding: on the
    deployment there is no local engine, and the recording is sent to
    Cloudflare. Describing a privacy posture the code no longer has is worse
    than never having described one.

    What is still true: the audio is **not stored** — not here, not in the
    Worker, not in any database. It is held in memory for one request and the
    transcript is what survives.

    The original reasoning stands and is why this is worth saying out loud: text
    is disposable and a voice is biometric. Running `cli serve` locally with
    whisper.cpp keeps it on your own machine; the hosted app cannot.
    """
    from .providers import asr

    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="no audio")
    if len(audio) > 12_000_000:
        raise HTTPException(status_code=413, detail="recording too long")
    mime = request.headers.get("content-type", "audio/wav").split(";")[0]
    # The question being answered, passed through as Whisper's initial_prompt:
    # a few seconds of accented Estonian is exactly what a recogniser guesses
    # wrong on, and the topic's vocabulary is a free hint.
    context = request.query_params.get("q", "")[:220]
    target = request.query_params.get("target", "")[:400]
    result = asr.transcribe(audio, mime, context=context or target).to_dict()

    # Read-aloud: the target is known, so the comparison is deterministic and
    # carries no model judgement. This is the part that *is* measurable — see
    # eesti/pronunciation.py for why it is not the same as scoring pronunciation.
    if target and result.get("text"):
        from .pronunciation import compare

        result["comparison"] = compare(target, result["text"]).to_dict()
    return result


class TranscriptIn(BaseModel):
    """A transcript the platform already produced. See `transcribe_text`."""

    text: str = Field(default="", max_length=4000)
    engine: str = Field(default="", max_length=120)
    degraded: bool = False
    note: str = Field(default="", max_length=400)


@app.post("/api/transcribe/text")
def transcribe_text(blob: TranscriptIn, request: Request) -> dict:
    """Grade a transcript the Worker recognised, rather than recognising it here.

    Cloudflare Workers AI is reachable two ways: over REST with an API token, or
    through the Worker's own `AI` binding. The binding wins on every count that
    matters here. It needs no token at all, so the origin never holds a
    credential that can edit Workers; it runs recognition on the platform the
    app is already fronted by; and it keeps the split this project is built on
    intact -- **a model may say what it heard, and nothing else.**

    Everything downstream of the transcript stays here and stays deterministic:
    the target sentence is known, so `compare` is string alignment, not
    judgement. That is the whole reason read-aloud can be scored honestly while
    pronunciation cannot.

    `/api/transcribe` remains for local `cli serve`, where there is no Worker and
    the provider chain does the recognising.
    """
    result = blob.model_dump()
    target = request.query_params.get("target", "")[:400]
    if target and blob.text:
        from .pronunciation import compare

        result["comparison"] = compare(target, blob.text).to_dict()
    return result


@app.get("/api/speaking/readaloud")
def read_aloud(kind: str = "lause", n: int = 8, levels: str = "A1,A2,B1",
               seed: int | None = None) -> dict:
    """Things to say out loud, with a known target so the result is checkable."""
    from .pronunciation import sentences_to_say, words_to_say

    if kind == "sona":
        items = words_to_say(db(), tuple(levels.split(",")), count=n, seed=seed)
    elif kind == "lause":
        items = sentences_to_say(content_db(), count=n, seed=seed)
    else:
        raise HTTPException(status_code=400, detail="kind must be sona or lause")
    return {"kind": kind, "items": [i.to_dict() for i in items]}


class SpokenAnswer(BaseModel):
    transcript: str = Field(min_length=1, max_length=4000)
    question: str = ""
    seconds: float = 0.0


@app.post("/api/speaking/feedback")
def speaking_feedback(req: SpokenAnswer) -> dict:
    """Feedback on an open spoken answer — on the words, not on the sounds.

    Once there is a transcript, a spoken answer is text, and this project
    already knows what to do with Estonian text: the same grammar chain that
    checks writing, and the same vocabulary tables that measure a reading. What
    it still refuses to do is grade the audio.

    Pace is reported only when the client supplies a duration, and as a plain
    number: 100-130 words a minute is ordinary conversational Estonian, and a
    learner reading haltingly will see why the number is low without anyone
    inventing a fluency score.
    """
    from .lookup import annotate
    from .providers import grammar as grammar_provider

    # A transcript is evidence about two things at once — what was said and what
    # the model heard — and nothing here can separate them, so the result is
    # re-read as advisory and the recogniser-shaped corrections are dropped.
    checked = grammar_provider.from_transcript(
        grammar_provider.check(req.transcript), req.transcript
    )
    words = req.transcript.split()
    profile = annotate(req.transcript)

    pace = None
    if req.seconds > 0:
        pace = round(len(words) / (req.seconds / 60), 1)

    return {
        "corrections": [c.to_dict() if hasattr(c, "to_dict") else c
                        for c in checked.corrections],
        "engine": checked.engine,
        "degraded": checked.degraded,
        "advisory": checked.advisory,
        "words": len(words),
        "pace_wpm": pace,
        "vocabulary": {
            "known_levels": profile.get("levels", {}) if isinstance(profile, dict) else {},
        },
        "note": (
            "Sisu ja grammatika kohta — mitte häälduse. Kõnetuvastus võib olla "
            "valesti kuulnud, nii et need on vihjed, mitte kinnitatud vead: "
            "vigade logisse need ei lähe."
        ),
    }


# --------------------------------------------------------------------------
# State snapshots — the thing that stops a deploy eating the learner's progress
# --------------------------------------------------------------------------
#
# Cloudflare Containers have **ephemeral disk**: "when a Container instance goes
# to sleep, the next time it is started, it will have a fresh disk as defined by
# its container image." With a ten-minute sleep timer, that means every coffee
# break would reset mastery, the review queue and the vocabulary table — the
# state that steps 3 to 9 exist to accumulate.
#
# So the durable copy lives outside the container, in the Durable Object that
# manages it, and these two endpoints are how it gets in and out. Only the
# *learner's* databases travel: the word list, the form index and the harvested
# corpus are derived or baked into the image, so shipping them would be copying
# 58 MB to say nothing.

STATE_DATABASES = ("progress", "review", "vocab")


def _state_paths() -> dict[str, Path]:
    return {
        "progress": Path(PROGRESS_DB),
        "review": Path(REVIEW_DB),
        "vocab": Path(VOCAB_DB),
        # Queued corrections are learner data like any other. Leaving this out
        # meant every error waiting for review evaporated on the next cold
        # start -- and Cloud Run cold-starts after minutes of idling, so a queue
        # whose whole purpose is to hold things until a person looks at them
        # held nothing across a coffee break.
        "notion": Path(NOTION_DB),
    }


def _require_state_token(request: Request) -> None:
    """Snapshots are for the platform, not for the browser.

    Cloudflare Access already gates the whole app, but a restore endpoint
    overwrites everything the learner has done, so it does not rely on a single
    layer. With no token configured the endpoints refuse outright rather than
    defaulting to open — an unset secret is a misconfiguration, not permission.
    """
    expected = os.environ.get("STATE_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="STATE_TOKEN is not configured")
    if not hmac.compare_digest(request.headers.get("x-state-token", ""), expected):
        raise HTTPException(status_code=403, detail="bad state token")


class ResetRequest(BaseModel):
    topic: str | None = None
    everything: bool = False


@app.post("/api/progress/reset")
def progress_reset(req: ResetRequest, request: Request) -> dict:
    """Forget a topic's attempts.

    Guarded by `STATE_TOKEN` rather than left open behind Access, for the same
    reason the snapshot endpoints are: this destroys learner history, and a
    misfired request from a page the learner has open should not be able to do
    that. It is an operator action, not a UI button.

    Clearing everything must be asked for explicitly. A missing `topic` is far
    more likely to be a bug in a caller than a genuine wish to erase months of
    work, so it is refused unless `everything` says otherwise.
    """
    _require_state_token(request)
    from .progress import reset

    if not req.topic and not req.everything:
        raise HTTPException(
            status_code=400,
            detail="Pass a topic, or everything=true to clear all of it.",
        )
    return reset(progress_db(), req.topic)


@app.get("/api/state/export")
def state_export(request: Request) -> dict:
    """The learner's databases, base64'd, for the Worker to persist."""
    _require_state_token(request)
    out = {}
    for name, path in _state_paths().items():
        out[name] = (
            base64.b64encode(path.read_bytes()).decode("ascii")
            if path.exists() else ""
        )
    return {"databases": out, "bytes": sum(len(v) for v in out.values())}


class StateBlob(BaseModel):
    databases: dict[str, str]


# The table that means "this learner has actually done something" in each
# database. Existence of the file is not that: the first request to arrive
# creates it *with its schema*, so "the file is non-empty" is true of a
# completely fresh container.
LEARNER_ROWS = {
    "progress": "attempts",
    "review": "review_items",
    "vocab": "vocab_status",
    "notion": "notion_queue",
}


def _has_learner_data(path: Path, table: str) -> bool:
    """True only if there is real work in there worth protecting.

    Tested against a live container, which is how the bug this replaces was
    found: a fresh instance answered `/api/curriculum`, which created
    `progress.db` with an empty schema, and the restore that followed refused to
    overwrite it — silently discarding the snapshot it existed to restore.
    """
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > 0
    except sqlite3.Error:
        # Unreadable or not a database: not something worth preserving, but not
        # something to overwrite blindly either.
        return True


class ContentBlob(BaseModel):
    database: str = Field(min_length=1)


@app.post("/api/content/import")
def content_import(blob: ContentBlob, request: Request) -> dict:
    """Receive the harvested library, which cannot ship in the image.

    Two facts collide here. The corpus is **owner-only** -- ERR transcripts are
    © ERR, Selges keeles carries no reuse grant -- so it has no business inside
    an image built from a public repository. And Cloud Run's disk is
    **ephemeral**, so a file copied in by hand is gone at the next cold start.

    So it travels the same road the learner's progress does: held by the Worker,
    pushed in whenever a fresh instance appears. Harvest once on a laptop, push
    once, and every container after that gets it without the harvest ever
    running again -- which also keeps this app from re-scraping someone else's
    server on every deploy.

    Unlike the learner snapshot, this one **does** overwrite. The corpus is
    derived from a harvest, not accumulated by the learner: there is no work in
    it to lose, and refusing would make re-harvesting impossible.
    """
    _require_state_token(request)
    from . import config

    path = Path(config.CONTENT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(blob.database))

    from .sources import connect as _connect

    with _connect(path) as conn:
        items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    return {"bytes": path.stat().st_size, "items": items}


@app.get("/api/content/export")
def content_export(request: Request) -> dict:
    """Hand the library back, so the Worker can archive what was pushed here.

    Cloudflare Access guards the Worker, and Access is an interactive login: a
    script cannot satisfy it. So a harvest is pushed to *this* origin, which is
    guarded by `PROXY_TOKEN` and reachable by a machine -- and the Worker picks
    it up from here and keeps it, because this disk will not exist tomorrow.

    `full` is opt-in because the answer is megabytes. Without it this is a
    cheap "is there one, and how big", which is all the Worker needs to decide
    whether to ask for the expensive version.
    """
    _require_state_token(request)
    from . import config
    from .sources import available

    path = Path(config.CONTENT_DB)
    present = available(path)
    out = {
        "present": present,
        "bytes": path.stat().st_size if path.exists() else 0,
    }
    if present and request.query_params.get("full"):
        out["database"] = base64.b64encode(path.read_bytes()).decode("ascii")
    return out


@app.post("/api/state/import")
def state_import(blob: StateBlob, request: Request) -> dict:
    """Restore a snapshot into a fresh container.

    Refuses to overwrite a database that already holds **learner rows** — not
    merely one that exists. A restore racing a learner who has started answering
    would discard the newer work, and losing five minutes beats losing it
    silently; but an empty schema is not work, and treating it as such made the
    restore refuse every time, which is the failure the snapshot exists to
    prevent.
    """
    _require_state_token(request)
    restored, skipped = [], []
    for name, path in _state_paths().items():
        payload = blob.databases.get(name) or ""
        if not payload:
            continue
        if _has_learner_data(path, LEARNER_ROWS[name]):
            skipped.append(name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(payload))
        restored.append(name)
    return {"restored": restored, "skipped": skipped}
