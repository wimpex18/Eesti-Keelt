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
    """Sentences to write down, easiest first. An empty corpus is a supported state:
    200 with an empty list.
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
    from ..lookup import annotate
    from ..providers import grammar as grammar_provider

    # A transcript mixes what was said with what was heard, so the result is re-read
    # as advisory and recogniser-shaped corrections are dropped.
    checked = grammar_provider.from_transcript(
        grammar_provider.check(req.transcript), req.transcript
    )
    words = req.transcript.split()
    profile = annotate(req.transcript)

    pace = None
    if req.seconds > 0:
        pace = round(len(words) / (req.seconds / 60), 1)

    from .. import evidence

    # Advisory, so never in the error log or the review queue; kept as evidence
    # that speaking was practised, with what was heard.
    evidence.record("speech", {
        "kind": "open", "question": req.question, "transcript": req.transcript,
        "words": len(words), "seconds": req.seconds, "engine": checked.engine,
    })

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
            "О содержании и грамматике, не о произношении (hääldus). "
            "Распознавание речи могло ослышаться, поэтому это подсказки, а не "
            "подтверждённые ошибки: в журнал ошибок они не попадают."
        ),
    }
