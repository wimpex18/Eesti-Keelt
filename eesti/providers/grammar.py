"""Grammar checking, as a chain of interchangeable providers.

Order is deliberate: try the free Estonian-specific services first, fall back to
an LLM, and if even that is unavailable degrade to purely offline evidence
rather than failing. The user always sees which engine answered, because a
correction from Vabamorf-only mode carries far less authority than one with a
real explanation behind it.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Protocol

from ..config import PROVIDER_TIMEOUT, TAGS, TARTUNLP_GRAMMAR
from . import breaker

SYSTEM_PROMPT = """\
You are an Estonian teacher correcting a Russian-speaking learner preparing for \
the B1 tasemeeksam. Their #1 documented weakness is object case: using partitive \
(osastav) where a completed, whole object requires genitive (omastav).

Return ONLY valid JSON:
{"corrections":[{"wrong":"...","correct":"...","why":"...","tag":"..."}]}

Rules:
- "why" MUST be written in RUSSIAN, but keep Estonian grammar terms in Estonian
  (osastav, omastav, sihitis, täissihitis, osasihitis). Be concise: 1-2 sentences.
- "tag" MUST be exactly one of: %s
- Use "obj-case" for any genitive/partitive/nominative object-case error.
- "wrong" must be the exact substring from the learner's text, so it can be
  located and highlighted.
- If the text is already correct, return {"corrections":[]}. Do not invent errors.
""" % ", ".join(TAGS)


@dataclass(frozen=True)
class Correction:
    wrong: str
    correct: str
    why: str
    tag: str = "vocab"
    start: int | None = None
    end: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GrammarResult:
    engine: str
    corrections: list[Correction] = field(default_factory=list)
    degraded: bool = False
    note: str = ""
    # True when the input was not typed by the learner — a speech transcript,
    # where the recogniser may have introduced the "error" being reported.
    # Advisory results are shown and never recorded: they must not reach the
    # Notion log or the review queue, because a curated error log is only worth
    # keeping if everything in it actually happened.
    advisory: bool = False

    def to_dict(self) -> dict:
        return {
            "engine": self.engine,
            "degraded": self.degraded,
            "advisory": self.advisory,
            "note": self.note,
            "corrections": [c.to_dict() for c in self.corrections],
        }


# The circuit breaker moved to `breaker.py` when the speech chain needed the same
# thing: two copies of a stateful mechanism drift into two behaviours. These
# names stay as thin aliases so existing callers and tests keep working.
_breaker_open = breaker.is_open
_record_failure = breaker.record_failure
_record_success = breaker.record_success


def reset_breakers() -> None:
    """Clear breaker state — used by tests and by an explicit 'retry now'."""
    breaker.reset()


class GrammarProvider(Protocol):
    name: str

    def available(self) -> bool: ...
    def check(self, text: str) -> GrammarResult: ...


def _locate(text: str, corrections: list[Correction]) -> list[Correction]:
    """Attach character offsets so the UI can highlight the exact span."""
    located, cursor = [], 0
    for c in corrections:
        start = text.find(c.wrong, cursor) if c.wrong else -1
        if start < 0:
            start = text.find(c.wrong) if c.wrong else -1
        end = start + len(c.wrong) if start >= 0 else None
        if start >= 0:
            cursor = end
        located.append(
            Correction(c.wrong, c.correct, c.why, c.tag,
                       start if start >= 0 else None, end)
        )
    return located


class TartuNLPGrammar:
    """TartuNLP's public GEC service (tekstkorda.ut.ee / api.tartunlp.ai).

    Kept in the chain because it is free, Estonian-specific and MIT-licensed, but
    it was returning 500 on every request during research and its /v2
    explanations are Estonian-only with no language parameter. Short timeout: the
    observed failure mode is a 61s gateway timeout, which must never be inflicted
    on someone waiting to see their mistake.
    """

    name = "tartunlp"

    def __init__(self, timeout: float = PROVIDER_TIMEOUT):
        self.timeout = timeout

    def available(self) -> bool:
        return os.environ.get("EESTI_DISABLE_TARTUNLP") != "1"

    def check(self, text: str) -> GrammarResult:
        req = urllib.request.Request(
            TARTUNLP_GRAMMAR,
            data=json.dumps({"language": "et", "text": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read())

        corrections = [
            Correction(
                wrong=entry.get("original", ""),
                correct=entry.get("corrected", ""),
                # Explanations come back in Estonian only; label them so the
                # learner is not surprised by the language switch.
                why=(entry.get("explanations") or "").strip() or "(selgitus puudub)",
                tag="vocab",
            )
            for entry in payload.get("corrections", [])
            if entry.get("original") != entry.get("corrected")
        ]
        return GrammarResult(self.name, _locate(text, corrections))


class LLMGrammar:
    """LLM checker, prompted for this learner's gap and the fixed Notion tags.

    Primary engine in practice: the only option that explains in Russian and can
    assign tags that group with the existing error log.

    Works against any OpenAI-compatible provider (OpenRouter, Groq, Workers AI,
    Anthropic) so the deployment target can change without touching this class.
    Which one to prefer is a quality question, not a taste one — run
    `python -m eesti.cli eval --provider X` before switching.
    """

    def __init__(self, provider: str = "openrouter", model: str | None = None):
        self.provider_name = provider
        self.model = model
        self.name = f"llm:{provider}"

    def available(self) -> bool:
        from .llm import PROVIDERS

        provider = PROVIDERS.get(self.provider_name)
        return bool(provider and provider.available)

    def check(self, text: str) -> GrammarResult:
        from .llm import complete, parse_json

        payload = parse_json(
            complete(self.provider_name, SYSTEM_PROMPT, text, model=self.model)
        )
        corrections = [
            Correction(
                wrong=c.get("wrong", ""),
                correct=c.get("correct", ""),
                why=c.get("why", ""),
                tag=c.get("tag") if c.get("tag") in TAGS else "vocab",
            )
            for c in payload.get("corrections", [])
        ]
        return GrammarResult(self.name, _locate(text, corrections))


class VabamorfFallback:
    """Always-available offline mode: evidence without judgement.

    This cannot decide whether a partitive should have been genitive — that needs
    telicity, which is semantics. It reports what is objectively true (the case
    actually written, plus misspellings) and says so honestly, so the learner is
    never shown a guess dressed up as a correction.
    """

    name = "vabamorf-offline"

    def available(self) -> bool:
        return True

    def check(self, text: str) -> GrammarResult:
        from ..morph import misspellings, object_case_candidates

        corrections = [
            Correction(
                wrong=item["text"],
                correct=(item["suggestions"] or [""])[0],
                why="Слово не найдено в словаре Vabamorf. Проверь написание.",
                tag="vocab",
            )
            for item in misspellings(text)
        ]

        flagged = [
            Correction(
                wrong=t.text,
                correct="",
                why=(
                    f"«{t.text}» стоит в форме "
                    f"{'osastav (partitiiv)' if t.is_partitive else 'omastav (genitiiv)'}"
                    f" от «{t.lemma}». Действие завершено? Тогда нужен omastav. "
                    "Процесс, отрицание или часть? Тогда osastav."
                ),
                tag="obj-case",
                start=t.start,
                end=t.end,
            )
            for t in object_case_candidates(text)
        ]

        return GrammarResult(
            self.name,
            corrections + flagged,
            degraded=True,
            note=(
                "Офлайн-режим: показаны кандидаты на obj-case и опечатки, "
                "но без проверки правильности. Для полного разбора задай ключ "
                "любого провайдера: OPENROUTER_API_KEY, GROQ_API_KEY, "
                "CLOUDFLARE_API_TOKEN или ANTHROPIC_API_KEY."
            ),
        )


# Tags whose evidence a speech transcript cannot support.
#
# `vocab` is raised when Vabamorf does not recognise a word. On writing that is
# a spelling mistake. On a transcript it is overwhelmingly the *recogniser*
# inventing a word — a learner who says `kooli` correctly and is heard as
# `kohli` would be told they made a vocabulary error, and then an object-case
# error on top of the invented word. Two mistakes reported, none made.
#
# So a transcript drops them. The remaining tags are about the *shape* of what
# was said, which survives a mis-heard word or two; `vocab` is about the word
# itself, which is exactly what the recogniser may have got wrong.
SPEECH_UNSUPPORTED_TAGS = frozenset({"vocab"})


def unrecognised_words(text: str) -> set[str]:
    """Tokens Vabamorf does not know — on a transcript, the recogniser's inventions."""
    from ..morph import misspellings

    return {item["text"].casefold() for item in misspellings(text)}


def from_transcript(result: "GrammarResult", text: str = "") -> "GrammarResult":
    """Re-read a written-text check as what it is when the input was spoken.

    An ASR transcript is evidence about two things at once — what the learner
    said, and what the model heard — and nothing here can separate them. So:

    1. **Corrections anchored on a word Vabamorf does not recognise are dropped
       entirely**, whatever their tag. The first version only dropped the
       `vocab` ones, which was half a fix: a learner who says *kooli* correctly
       and is heard as *kohli* stopped being told they had a vocabulary error,
       and was still told the invented word was in the wrong case. If a token is
       not a word, nothing about that token is worth reporting.
    2. What remains is marked `advisory`, so nothing downstream files it as a
       confirmed error — it must never reach the Notion log or seed the review
       queue, because a curated error log is only worth keeping if everything in
       it actually happened.

    The unknown-word set is recomputed from the text rather than read off the
    `vocab` corrections, because an LLM provider may not emit those at all and
    the rule has to hold for every engine in the chain.
    """
    unknown = unrecognised_words(text) if text else {
        c.wrong.casefold() for c in result.corrections
        if c.tag in SPEECH_UNSUPPORTED_TAGS
    }
    kept = [
        c for c in result.corrections
        if c.tag not in SPEECH_UNSUPPORTED_TAGS
        and c.wrong.casefold().strip(".,!?;:") not in unknown
    ]
    return GrammarResult(
        result.engine,
        kept,
        degraded=result.degraded,
        advisory=True,
        note=(
            "Транскрипция речи: распознавание могло услышать не то, что ты "
            "сказал. Подсказки — не подтверждённые ошибки."
        ),
    )


# Preference order for LLM providers. Any provider that is not configured is
# skipped, so this degrades by configuration alone.
#
# `local` is first when it is switched on, and switched off by default. That
# order is not a guess about quality: it is the one lane running a model built
# for Estonian, and Estonian object case is the specific thing every general
# model here has been measured failing. It is also free, private and unmetered,
# so when it is available there is no argument for asking anyone else first.
#
# `huggingface` used to be in this list's place in `PROVIDERS` and was never in
# this list at all -- defined, unreachable, and unnoticed for exactly that
# reason. Anything added to `PROVIDERS` and not to this tuple is dead weight;
# a test now asserts the two agree.
LLM_PREFERENCE = ("local", "openrouter", "groq", "workers-ai", "anthropic")


def build_chain(providers: list[GrammarProvider] | None = None) -> list[GrammarProvider]:
    """Default order: Estonian-specific service, then LLMs, then offline.

    TartuNLP goes first because it is purpose-built for Estonian and free, but it
    was failing every request during development, so the breaker will normally
    step over it within a couple of calls.
    """
    if providers is not None:
        return providers
    return [
        TartuNLPGrammar(),
        *(LLMGrammar(name) for name in LLM_PREFERENCE),
        VabamorfFallback(),
    ]


#: `non-json` and `no-code` are this module's own words for "the provider did
#: not give one", and are deliberately shaped like the thing they stand in for
#: so the note reads the same either way. They are the two answers that used to
#: be silence.
#:
#: A machine-readable error identifier — `model_decommissioned`,
#: `invalid_api_key`, `rate_limit_exceeded`. Deliberately narrow: no spaces, no
#: capitals, no non-ASCII, and short. A learner's sentence cannot take this
#: shape, which is what makes reading this one field compatible with the rule
#: below that a response body never reaches the note.
_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_.-]{2,39}$")


def _error_code(exc: urllib.error.HTTPError) -> str:
    """The provider's own name for the failure, or "" if it did not give one.

    Every OpenAI-compatible provider in the chain answers a 4xx with
    `{"error": {"code": ..., "type": ...}}`, and that identifier is the
    difference between a status code and an instruction. Anything that is not
    such an identifier — prose, HTML from a proxy sitting in front of the API, a
    body that echoes the request — fails the pattern and is dropped rather than
    trimmed, because a truncated sentence is still a sentence.

    Reading is capped and never raises: this runs on the failure path, and an
    error while explaining an error would replace a useful note with none.
    """
    try:
        raw = exc.read(4096)
    except Exception:
        return ""
    if not raw:
        # No body at all -- a synthesised error, or a proxy that sent none.
        # There is nothing to report, and reporting the absence as `no-code`
        # would add a word to every 500 while saying less than the silence.
        return ""
    try:
        body = json.loads(raw or b"{}")
    except Exception:
        # Not the provider's JSON at all. Almost always something in *front* of
        # the API -- Groq, OpenRouter and Cloudflare all sit behind proxies that
        # answer 403 with an HTML challenge page, and that is a completely
        # different diagnosis from the API itself refusing. Saying nothing here
        # made the two identical, and an ambiguous note is what sent an hour
        # into deciding whether a deployment was even running the new code.
        return "non-json"
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return "no-code"
    for key in ("code", "type"):
        value = error.get(key)
        if isinstance(value, str) and _ERROR_CODE.match(value):
            return value
    # JSON, shaped like an error, and the identifier fields hold prose. Reported
    # as an absence rather than trimmed: a truncated sentence is still a
    # sentence, and this note is printed into CI logs.
    return "no-code"


def _why(exc: BaseException) -> str:
    """Name a failure precisely enough to act on it.

    The type alone is not actionable. `HTTPError` covers a 429 (wait, the free
    tier is spent), a 401 (the key is dead, replace it) and a 502 (the provider
    is having a moment) — three different jobs for the operator, printed
    identically. A live deployment reported `llm:openrouter: HTTPError` and
    nothing in the note could say which of the three it was.

    The status code was that fix, and it was the same fix one level too shallow.
    On 2026-08-22 a freshly-set Groq key reported `HTTPError 403` on its first
    call. 403 is *permissions*, so the diagnosis went to the key — and the key
    was fine: the pinned model id had been deprecated for free accounts six days
    earlier, and a withdrawn id that enterprise accounts still hold does not
    404, it forbids. The provider had named the cause in its body, and the note
    dropped it, so the answer came from a web search instead of from the run
    that hit it.

    Never a response *body*: the note is printed into CI logs, and the text
    being checked is the learner's own writing. `_error_code` reads one field
    and only when it is an identifier, which is a shape prose cannot take.
    """
    if isinstance(exc, urllib.error.HTTPError):
        code = _error_code(exc)
        return f"HTTPError {exc.code} ({code})" if code else f"HTTPError {exc.code}"
    return type(exc).__name__


def check(text: str, providers: list[GrammarProvider] | None = None) -> GrammarResult:
    """Run the chain, returning the first provider that answers.

    Failures are expected, not exceptional, so they are swallowed and recorded in
    the final result's note rather than raised.
    """
    tried: list[str] = []
    for provider in build_chain(providers):
        if not provider.available():
            tried.append(f"{provider.name}: unavailable")
            continue
        if _breaker_open(provider.name):
            tried.append(f"{provider.name}: skipped (recent failures)")
            continue
        try:
            result = provider.check(text)
            _record_success(provider.name)
            if tried:
                result.note = (result.note + " | " if result.note else "") + \
                    "skipped -> " + "; ".join(tried)
            return result
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            _record_failure(provider.name)
            tried.append(f"{provider.name}: {_why(exc)}")
        except Exception as exc:  # bad JSON, SDK errors — never fatal
            _record_failure(provider.name)
            tried.append(f"{provider.name}: {_why(exc)}")

    return GrammarResult("none", [], degraded=True, note="; ".join(tried))
