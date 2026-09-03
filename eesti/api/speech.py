"""Everything with sound in it: TTS, dictation, ASR and the speaking bank.

The recogniser is the one other place a model is allowed: it says what it
heard. It does not score. The pronunciation comparison carries its caveat in
Russian, because a miss may be the recogniser rather than the learner's mouth.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..providers import tts
from .deps import content_db, db, progress_db, vocab_db

router = APIRouter()

class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str = tts.DEFAULT_VOICE
    speed: float = Field(default=tts.LEARNER_SPEED, ge=0.5, le=2.0)


@router.post("/api/speak")
def speak(req: SpeakRequest) -> FileResponse:
    """Synthesize Estonian audio for arbitrary text — turns anything into listening practice."""
    try:
        path = tts.synthesize(req.text, speaker=req.voice, speed=req.speed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Синтез речи сейчас недоступен ({type(exc).__name__}). Попробуй позже."
        ) from exc
    return FileResponse(path, media_type="audio/wav", filename="eesti.wav")


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


@router.get("/api/dictation/next")
def dictation_next(count: int = 1, seed: int | None = None) -> dict:
    """Sentences to write down, easiest-first for this learner.

    The corpus is owner-only and supplied at runtime, so an empty library is a
    supported state and answers 200 with an empty list — the same contract the
    reading views use. A 404 here would read as a broken feature.
    """
    from ..dictation import CAVEAT, MAX_WORDS, MIN_WORDS, choose

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
        # Both of these EXPLAIN, so both are Russian: one says how the
        # exercise works, the other says why there is no exercise and what
        # would produce one. The second was the worse failure -- it is the
        # only thing standing between the learner and an empty panel.
        "note": ("Прослушай и запиши услышанное. Слушать можно сколько нужно."
                 if passages else
                 "Корпус текстов пуст, поэтому диктантов (etteütlus) сейчас "
                 "нет. Они появятся, когда материал будет загружен: "
                 "`cli harvest-reading` или `cli ingest`."),
    }


@router.post("/api/dictation/answer")
def dictation_answer(req: DictationAnswer) -> dict:
    """Grade a submission, and write it down.

    Graded server-side for the same reason every other answer is: a page can
    be edited, and a score the browser computed measures nothing. Recorded in
    the same call, because a listening exercise whose result nothing stores is
    how the verdict came to report this part as untouched no matter how much
    had been played.
    """
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
    from ..providers import asr

    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Запись пустая — ничего не записалось.")
    if len(audio) > 12_000_000:
        raise HTTPException(status_code=413, detail="Запись слишком длинная. Скажи короче — до пары предложений.")
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
        from ..pronunciation import compare

        result["comparison"] = compare(target, result["text"]).to_dict()
    return result


class TranscriptIn(BaseModel):
    """A transcript the platform already produced. See `transcribe_text`."""

    text: str = Field(default="", max_length=4000)
    engine: str = Field(default="", max_length=120)
    degraded: bool = False
    note: str = Field(default="", max_length=400)


@router.post("/api/transcribe/text")
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
        from ..pronunciation import compare

        result["comparison"] = compare(target, blob.text).to_dict()
    return result


@router.get("/api/speaking/readaloud")
def read_aloud(kind: str = "lause", n: int = 8, levels: str = "A1,A2,B1",
               seed: int | None = None) -> dict:
    """Things to say out loud, with a known target so the result is checkable."""
    from ..pronunciation import sentences_to_say, words_to_say

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


@router.post("/api/speaking/feedback")
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
    from ..lookup import annotate
    from ..providers import grammar as grammar_provider

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
