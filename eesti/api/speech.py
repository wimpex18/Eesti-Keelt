"""Everything with sound in it: TTS, dictation, ASR and the speaking bank.

The recogniser is the one other place a model is allowed: it says what it
heard. It does not score. The pronunciation comparison carries its caveat in
Russian, because a miss may be the recogniser rather than the learner's mouth.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from ..providers import tts
from .deps import content_db, db, progress_db, vocab_db

router = APIRouter()

class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str = tts.DEFAULT_VOICE
    speed: float = Field(default=tts.LEARNER_SPEED, ge=0.5, le=2.0)


def _human(text: str) -> Response | None:
    """EKI's own reader saying exactly this sentence, if we have it.

    A real reader is what the exam plays, and Estonian quantity is audible in a
    way synthesis does not reliably produce (`eesti/haaldus.py`).
    """
    from .. import config, haaldus

    if not Path(config.AUDIO_DB).exists():
        return None
    row = haaldus.said(haaldus.connect(config.AUDIO_DB), text)
    if row is None:
        return None
    return Response(
        content=row["audio"], media_type=row["mime"],
        headers={"cache-control": "public, max-age=31536000, immutable",
                 "x-audio-source": row["source"]})


def _spoken(text: str, voice: str, speed: float) -> FileResponse:
    """The audio for one sentence, synthesised or served from the disk cache.

    The same sentence in the same voice at the same speed is the same audio
    forever, so the response says so: the Worker's edge cache keeps it, and a
    cold start stops costing TartuNLP a request per sentence again
    (`deploy/worker.ts`, `docs/speaking.md`).
    """
    try:
        path = tts.synthesize(text, speaker=voice, speed=speed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Синтез речи сейчас недоступен ({type(exc).__name__}). Попробуй позже."
        ) from exc
    return FileResponse(
        path, media_type="audio/wav", filename="eesti.wav",
        headers={"cache-control": "public, max-age=31536000, immutable"})


@router.post("/api/speak")
def speak(req: SpeakRequest):
    """Estonian audio for any text: a human reading where EKI recorded one,
    synthesis otherwise."""
    return _human(req.text) or _spoken(req.text, req.voice, req.speed)


@router.get("/api/speak")
def speak_get(text: str, voice: str = tts.DEFAULT_VOICE,
              speed: float = tts.LEARNER_SPEED):
    """The same audio, addressable by URL so it can be cached.

    A POST body cannot be a cache key; a URL can. The page uses this for
    anything it plays more than once (a dictation sentence, an exam prompt).
    """
    if len(text) > 400:
        raise HTTPException(status_code=400, detail="Слишком длинный текст для ссылки.")
    return _human(text) or _spoken(text, voice, speed)


@router.get("/api/speaking")
def speaking_bank(kind: str | None = None) -> dict:
    """Questions in the exam's shape. No scoring — see `eesti/speaking.py`."""
    from ..speaking import KINDS, bank

    return {
        "kinds": KINDS,
        "questions": [
            {"topic": q.topic, "question": q.question, "hint_ru": q.hint_ru,
             "kind": q.kind}
            for q in bank(kind)
        ],
    }


class DictationAnswer(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    typed: str = Field(default="", max_length=800)


def _human_passages(count: int, seed: int | None) -> list:
    """Dictation from sentences a person actually read, when we have them.

    A synthesised dictation teaches the synthesiser's endings; the exam plays a
    person. Falls back to the corpus when no recordings are imported.
    """
    import random

    from .. import config, haaldus
    from ..dictation import MAX_WORDS, MIN_WORDS, Passage, key_of

    if not Path(config.AUDIO_DB).exists():
        return []
    try:
        conn = haaldus.connect(config.AUDIO_DB)
        texts = [t for t in haaldus.spoken_sentences(conn, max_words=MAX_WORDS)
                 if MIN_WORDS <= len(t.split()) <= MAX_WORDS]
    except Exception:  # noqa: BLE001 - no recordings is a state, not an error
        return []
    if not texts:
        return []
    random.Random(seed).shuffle(texts)
    return [Passage(text, key_of(text), len(text.split())) for text in texts[:count]]


@router.get("/api/dictation/next")
def dictation_next(count: int = 1, seed: int | None = None) -> dict:
    """Sentences to write down, easiest first. An empty corpus is a supported state:
    200 with an empty list.
    """
    from ..dictation import CAVEAT, MAX_WORDS, MIN_WORDS, choose

    try:
        content = content_db()
    except Exception:  # noqa: BLE001 - no corpus is a state, not an error
        content = None
    passages = _human_passages(max(1, min(count, 10)), seed)
    if not passages:
        passages = choose(
            content, vocabulary=vocab_db(), count=max(1, min(count, 10)), seed=seed,
        ) if content is not None else []
    return {
        "passages": [p.to_dict() for p in passages],
        "words": [MIN_WORDS, MAX_WORDS],
        "caveat": CAVEAT,
        # Both explain, so both are Russian: how the exercise works, and why there is no
        # exercise and what would produce one.
        "note": ("Прослушай и запиши услышанное."
                 if passages else
                 "Диктанты (etteütlus) берутся из корпуса текстов, а его ещё "
                 "не добавили в приложение."),
    }


@router.post("/api/dictation/answer")
def dictation_answer(req: DictationAnswer) -> dict:
    """Grade a submission server-side and record it in the same call."""
    from ..dictation import Passage, grade, key_of, record

    passage = Passage(req.text, key_of(req.text), len(req.text.split()))
    result = grade(passage, req.typed)
    record(progress_db(), result)
    return result.to_dict()


@router.get("/api/asr")
def asr_available() -> dict:
    """Which speech engines this deployment can use — shown in the UI as-is."""
    from ..providers import asr

    return asr.available()


@router.post("/api/transcribe")
async def transcribe(request: Request) -> dict:
    """Transcribe a recording. Optional everywhere: no engine is still a 200.

    On the deployment, recognition runs on Cloudflare Workers AI via the Worker, so
    the recording leaves the device; the audio is held in memory for one request and
    never stored. Under `cli serve` with local whisper.cpp it stays on the machine.
    """
    from ..providers import asr

    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Запись пустая — ничего не записалось.")
    if len(audio) > 12_000_000:
        raise HTTPException(status_code=413, detail="Запись слишком длинная. Скажи короче — до пары предложений.")
    mime = request.headers.get("content-type", "audio/wav").split(";")[0]
    # The question being answered, passed through as Whisper's initial_prompt:
    # a few seconds of accented Estonian is exactly what a recogniser guesses
    # wrong on, and the topic's vocabulary is a free hint. Never the read-aloud
    # target: priming the recogniser with the words it is about to be compared
    # against makes it hear them whether or not they were said.
    context = request.query_params.get("q", "")[:220]
    target = request.query_params.get("target", "")[:400]
    result = asr.transcribe(audio, mime, context=context).to_dict()

    # Read-aloud: the target is known, so the comparison is deterministic and
    # carries no model judgement. This is the part that *is* measurable — see
    # eesti/pronunciation.py for why it is not the same as scoring pronunciation.
    if target and result.get("text"):
        from ..pronunciation import compare

        result["comparison"] = compare(target, result["text"]).to_dict()
        _record_read_aloud(target, result)
    return result


def _record_read_aloud(target: str, result: dict) -> None:
    """A read-aloud attempt as evidence: the transcript, never the audio."""
    from .. import evidence

    c = result["comparison"]
    evidence.record("speech", {
        "kind": "read-aloud", "target": target, "transcript": result["text"],
        "engine": result.get("engine", ""), "matched": c["matched"],
        "total": c["total"],
    })


class TranscriptIn(BaseModel):
    """A transcript the platform already produced. See `transcribe_text`."""

    text: str = Field(default="", max_length=4000)
    engine: str = Field(default="", max_length=120)
    degraded: bool = False
    note: str = Field(default="", max_length=400)


@router.post("/api/transcribe/text")
def transcribe_text(blob: TranscriptIn, request: Request) -> dict:
    """Grade a transcript the Worker recognised via its `AI` binding (no API token on
    the origin). The target sentence is known, so comparison is deterministic string
    alignment. `/api/transcribe` remains for local `cli serve`.
    """
    result = blob.model_dump()
    target = request.query_params.get("target", "")[:400]
    if target and blob.text:
        from ..pronunciation import compare

        result["comparison"] = compare(target, blob.text).to_dict()
        _record_read_aloud(target, result)
    return result


@router.get("/api/speaking/readaloud")
def read_aloud(kind: str = "lause", n: int = 8, levels: str = "A1,A2,B1",
               seed: int | None = None) -> dict:
    """Things to say out loud, with a known target so the result is checkable."""
    from ..pronunciation import sentences_to_say, words_to_say

    if kind == "sona":
        items = words_to_say(db(), tuple(levels.split(",")), count=n, seed=seed)
    elif kind == "lause":
        from ..difficulty import known_lemmas

        items = sentences_to_say(content_db(), count=n, seed=seed, words=db(),
                                 known=known_lemmas(vocab_db()))
    else:
        raise HTTPException(status_code=400, detail="kind must be sona or lause")
    return {"kind": kind, "items": [i.to_dict() for i in items]}


class SpokenAnswer(BaseModel):
    transcript: str = Field(min_length=1, max_length=4000)
    question: str = ""
    seconds: float = 0.0


@router.post("/api/speaking/feedback")
def speaking_feedback(req: SpokenAnswer) -> dict:
    """Feedback on an open spoken answer — on the words, not the sounds.

    The transcript goes through the writing grammar chain and the vocabulary
    tables. Pace is reported as a plain words-per-minute number only when the client
    sends a duration.
    """
    from .. import tutor
    from ..lookup import annotate

    # A transcript mixes what was said with what was heard, so the result is re-read
    # as advisory and recogniser-shaped corrections are dropped (ADR-0002: the
    # tutor is the one boundary a model is called across).
    checked = tutor.speaking_feedback(req.transcript)
    words = req.transcript.split()
    profile = annotate(req.transcript)

    pace = None
    if req.seconds > 0:
        pace = round(len(words) / (req.seconds / 60), 1)

    from .. import evidence
    from ..learner import speech_signals

    # Advisory, so never in the error log or the review queue; kept as evidence
    # that speaking was practised, with what code can measure about it.
    signals = speech_signals(req.transcript, req.seconds)
    evidence.record("speech", {
        "kind": "open", "question": req.question, "transcript": req.transcript,
        "words": len(words), "seconds": req.seconds, "engine": checked["engine"],
        **signals,
    })

    return {
        "corrections": checked["corrections"],
        "engine": checked["engine"],
        "degraded": checked["degraded"],
        "advisory": checked["advisory"],
        "words": len(words),
        "pace_wpm": pace,
        # What code can say about a spoken answer, and nothing more: how much
        # was said, how fast, and how sure the transcript looks. Never a score.
        "signals": signals,
        "vocabulary": {
            "known_levels": profile.get("levels", {}) if isinstance(profile, dict) else {},
        },
        "note": (
            "О содержании и грамматике, не о произношении (hääldus). "
            "Распознавание речи могло ослышаться, поэтому это подсказки, а не "
            "подтверждённые ошибки: в журнал ошибок они не попадают."
        ),
    }


# --------------------------------------------------------------------------
# Recording the speech eval set (local only)
# --------------------------------------------------------------------------
#
# The set that decides which recogniser to use is the learner's own voice
# (ADR-0003), and the only way to get it is to record it. That is a local
# errand: this route writes audio to `data/eval/asr/` and refuses to exist on
# the deployment, where `PROXY_TOKEN` is set. The audio stays on the machine.

@router.post("/api/eval/clip")
async def eval_clip(request: Request) -> dict:
    """Save one recording with what was said, for `cli eval --suite asr`."""
    import os
    import re as _re

    from ..evals.asr import SET

    if os.environ.get("PROXY_TOKEN"):
        raise HTTPException(status_code=404, detail=(
            "Запись набора для оценки — локальная задача (`cli serve`)."))

    said = request.query_params.get("text", "").strip()
    planted = request.query_params.get("planted", "").strip()
    if not said:
        raise HTTPException(status_code=400, detail="Нужен текст, который читали.")
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Запись пустая.")

    SET.mkdir(parents=True, exist_ok=True)
    suffix = ".webm" if "webm" in request.headers.get("content-type", "") else ".wav"
    # A name that cannot collide with an existing clip, however many there are.
    taken = {p.stem for p in SET.glob("*")}
    n = len(taken)
    while f"{n:04d}" in taken:
        n += 1
    stem = f"{n:04d}"
    (SET / f"{stem}{suffix}").write_bytes(audio)
    (SET / f"{stem}.txt").write_text(said, encoding="utf-8")
    if planted:
        (SET / f"{stem}.said").write_text(planted, encoding="utf-8")
    clips = len(list(SET.glob("*.txt")))
    return {"saved": stem, "clips": clips, "planted": bool(planted),
            "folder": str(SET),
            "note": _re.sub(r"\s+", " ", """
                Запись сохранена только на этой машине. Для сравнения движков
                нужно 80–150 фраз, примерно четверть — с намеренной ошибкой.
            """).strip()}


@router.get("/api/eval/prompt")
def eval_prompt(planted: bool = False, seed: int | None = None) -> dict:
    """A sentence to read for the eval set.

    With `planted`, the sentence carries a deliberately wrong form — the
    distractor an object-case drill would have offered — because the measure
    that decides the engine is how often a mistake comes back *corrected*
    (ADR-0003).
    """
    import os
    import secrets

    from ..item import BLANK

    if os.environ.get("PROXY_TOKEN"):
        raise HTTPException(status_code=404, detail=(
            "Запись набора для оценки — локальная задача (`cli serve`)."))
    seed = seed if seed is not None else secrets.randbelow(2**31)

    if planted:
        from ..practice import items_for

        items = [i for i in items_for("obj-case", count=6, seed=seed)
                 if getattr(i, "distractor", "")]
        if not items:
            raise HTTPException(status_code=503, detail="Заданий сейчас нет.")
        item = items[0]
        return {"text": item.prompt.replace(BLANK, item.distractor),
                "planted": item.distractor, "correct": item.answer,
                "note": ("Прочитай вслух **как написано** — форма здесь "
                         "намеренно неверная. Так проверяется, не «исправит» "
                         "ли движок ошибку за тебя.")}

    from ..difficulty import known_lemmas
    from ..pronunciation import sentences_to_say

    try:
        content = content_db()
    except Exception:  # noqa: BLE001 - no corpus is a state, not an error
        raise HTTPException(status_code=503, detail=(
            "Для этого нужен корпус текстов, а он не загружен.")) from None
    said = sentences_to_say(content, count=1, seed=seed, words=db(),
                            known=known_lemmas(vocab_db()))
    if not said:
        raise HTTPException(status_code=503, detail="Предложений сейчас нет.")
    return {"text": said[0].text, "planted": "", "correct": "",
            "note": "Прочитай вслух как есть."}


# --------------------------------------------------------------------------
# A human voice for a word form (EKI's recordings)
# --------------------------------------------------------------------------

@router.get("/api/pronounce")
def pronounce(form: str, tag: str = "") -> Response:
    """EKI's own recording of a word form, or 404 so the caller falls back to TTS.

    Synthesis gets Estonian quantity wrong (`koera` vs `k`oera`); these are read
    by native speakers, and the form EKI wrote — marks and all — comes back in
    the `x-spoken-form` header so the page can show what was actually said
    (`eesti/haaldus.py`).
    """
    from .. import config, haaldus

    if not form.strip():
        raise HTTPException(status_code=400, detail="Нужна форма слова.")
    if not Path(config.AUDIO_DB).exists():
        raise HTTPException(status_code=404, detail=(
            "Записи произношения не загружены на этот сервер."))
    row = haaldus.spoken(haaldus.connect(config.AUDIO_DB), form.strip(), tag or None)
    if row is None:
        raise HTTPException(status_code=404, detail="Для этой формы записи нет.")
    return Response(
        content=row["audio"], media_type=row["mime"],
        headers={"cache-control": "public, max-age=31536000, immutable",
                 "x-spoken-form": quote(row["spoken"]),
                 "x-audio-source": row["source"]})
