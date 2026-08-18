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
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Protocol

from ..config import PROVIDER_TIMEOUT, TAGS, TARTUNLP_GRAMMAR

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

    def to_dict(self) -> dict:
        return {
            "engine": self.engine,
            "degraded": self.degraded,
            "note": self.note,
            "corrections": [c.to_dict() for c in self.corrections],
        }


# Circuit breaker. A research endpoint that is down tends to stay down for
# hours, and paying its timeout on every single check makes the tool feel broken.
# After a few consecutive failures we skip it for a while and retry later.
_BREAKER_THRESHOLD = 2
_BREAKER_COOLDOWN = 900.0  # seconds
_failures: dict[str, tuple[int, float]] = {}


def _breaker_open(name: str) -> bool:
    count, last = _failures.get(name, (0, 0.0))
    return count >= _BREAKER_THRESHOLD and (time.monotonic() - last) < _BREAKER_COOLDOWN


def _record_failure(name: str) -> None:
    count, _ = _failures.get(name, (0, 0.0))
    _failures[name] = (count + 1, time.monotonic())


def _record_success(name: str) -> None:
    _failures.pop(name, None)


def reset_breakers() -> None:
    """Clear breaker state — used by tests and by an explicit 'retry now'."""
    _failures.clear()


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


# Preference order for LLM providers. Free tiers first — at a few checks a day
# they are ample — with a paid model last as the quality backstop. Any provider
# whose key is unset is skipped, so this degrades by configuration alone.
LLM_PREFERENCE = ("openrouter", "groq", "workers-ai", "anthropic")


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
            tried.append(f"{provider.name}: {type(exc).__name__}")
        except Exception as exc:  # bad JSON, SDK errors — never fatal
            _record_failure(provider.name)
            tried.append(f"{provider.name}: {type(exc).__name__}")

    return GrammarResult("none", [], degraded=True, note="; ".join(tried))
