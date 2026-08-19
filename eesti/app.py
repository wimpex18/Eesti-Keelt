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

REVIEW_DB = "data/review.db"
PROGRESS_DB = "data/progress.db"
VOCAB_DB = "data/vocab.db"


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
    }


@app.post("/api/check")
def check(req: CheckRequest) -> dict:
    """Grammar check through the provider chain."""
    return grammar.check(req.text).to_dict()


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


@app.get("/api/library")
def library(skill: str = "lugemine", level: str | None = None, limit: int = 60) -> dict:
    """Harvested study material.

    `public_only` is deliberately NOT exposed as a parameter. This server is the
    single-user local one; the public deployment sets it, and making it a query
    parameter would let a caller ask for owner-only material by guessing.
    """
    conn = content_db()
    rows = content_query(conn, skill=skill, level=level, limit=limit)
    return {
        "items": [
            {
                "id": r["id"],
                "title": r["title"],
                "level": r["level"],
                "source": r["source_name"],
                "licence": r["licence"],
                "audio_url": r["audio_url"],
                "words": len(( r["body"] or "").split()),
            }
            for r in rows
        ]
    }


@app.get("/api/library/{item_id}")
def library_item(item_id: str) -> dict:
    """One item with its full text and a vocabulary profile."""
    conn = content_db()
    row = conn.execute(
        """SELECT i.*, s.name AS source_name, s.licence
           FROM items i JOIN sources s ON s.id = i.source_id
           WHERE i.id = ?""",
        (item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": row["id"],
        "title": row["title"],
        "body": row["body"],
        "level": row["level"],
        "source": row["source_name"],
        "licence": row["licence"],
        "audio_url": row["audio_url"],
        "profile": annotate(row["body"] or ""),
    }


@app.get("/api/grammar")
def grammar_rules() -> dict:
    """Every rule the app drills, linked to its section in the EKK handbook.

    Explanations point at the authority (Eesti keele käsiraamat) rather than
    restating it, so a learner who doubts a drill can check the source — and so
    we are not maintaining a parallel grammar that can drift.
    """
    return {"rules": [describe_rule(tag) for tag in REFERENCES]}


@app.get("/api/grammar/{tag}")
def grammar_rule(tag: str) -> dict:
    rule = describe_rule(tag)
    if not rule["known"]:
        raise HTTPException(status_code=404, detail=f"no reference for {tag!r}")
    return rule


@app.get("/api/word/{lemma}")
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
                "id": i.id, "kind": i.kind, "lemma": i.lemma,
                "prompt": i.prompt, "answer": i.answer,
                "distractor": i.distractor, "why_ru": i.why_ru,
                "context": i.context, "reps": i.reps, "lapses": i.lapses,
            }
            for i in items
        ]
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


@app.post("/api/review/failed")
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
    return {
        "resume": resume(progress),
        "mastered": sum(1 for r in rows if r.state == "mastered"),
        "total": len(rows),
        "topics": [
            {
                "id": r.topic, "level": r.level, "et": r.et, "state": r.state,
                "attempts": r.attempts, "accuracy": r.accuracy,
                "blocked_by": list(r.blocked_by),
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
    return {
        "topic": topic,
        "level": meta.level,
        "et": meta.et,
        "ru": meta.ru,
        "reference": describe_rule(meta.tag) if meta.tag else None,
        "items": [i.to_dict() for i in items],
    }


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

    return {
        "correct": correct,
        "answer": req.answer,
        "why_ru": req.why_ru,
        "accuracy": accuracy(progress, req.topic),
        "mastered": mastered_now,
        "just_mastered": mastered_now and not was_mastered,
        "gate": f"{MASTERY_CORRECT}/{MASTERY_WINDOW}",
    }


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


@app.get("/api/vocab")
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


@app.get("/api/asr")
def asr_available() -> dict:
    """Which speech engines this deployment can use — shown in the UI as-is."""
    from .providers import asr

    return asr.available()


@app.post("/api/transcribe")
async def transcribe(request: Request) -> dict:
    """Transcribe a recording. Optional everywhere: no engine is still a 200.

    The audio is not stored. A voice is biometric where text is disposable, so
    the local engine is preferred and nothing is written to disk beyond the
    temporary file whisper.cpp needs.
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
