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
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Protocol

from ..config import PROVIDER_TIMEOUT, TAGS, TARTUNLP_GRAMMAR
from . import breaker

# Why the object-case rules and the "most text is already correct" line are
# stated here and not just in the eval's prompt.
#
# `evals/gec.py` records the failure that produced them: on its first real run a
# model flagged four of eight already-correct sentences -- "Ma ostsin uue auto",
# "Ma sõin suppi". The fix was to state the rules *positively*, so a correct
# genitive is recognisably correct rather than merely un-flagged, and to resolve
# ambiguity toward saying nothing.
#
# That fix went into the eval's prompt and not into this one, which is the
# prompt the learner actually meets. The two had drifted apart on exactly the
# axis the eval measures, so a good eval score was a score for a prompt this app
# does not ship. A checker that invents errors teaches that every partitive is a
# mistake, which is worse than no checker at all.
#
# The worked examples are deliberately *not* copied across with them: this
# prompt's contract has a fourth field (`why`, in Russian) that the eval's
# three-field examples would contradict, and an example that disagrees with the
# contract above it is worse than none.
SYSTEM_PROMPT = """\
You are an Estonian teacher correcting a Russian-speaking learner preparing for \
the B1 tasemeeksam. Their #1 documented weakness is object case: using partitive \
(osastav) where a completed, whole object requires genitive (omastav).

OBJECT CASE — the rules, stated positively:
- Completed action, whole object -> GENITIVE (omastav). "Ma ostsin uue auto" is
  CORRECT. "Ma lugesin raamatu läbi" is CORRECT.
- Ongoing, repeated, or partial action -> PARTITIVE (osastav). "Ma sõin suppi"
  is CORRECT. "Ta luges raamatut terve õhtu" is CORRECT.
- Negation -> ALWAYS PARTITIVE. "Ma ei ostnud piletit" is CORRECT.

Most text you see is already correct. Report a correction ONLY where you are
confident a rule above is broken. Never flag a sentence merely because it
contains a partitive or a genitive — both are correct in their own context.

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


def _minimal_span(wrong: str, right: str) -> tuple[str, str]:
    """Narrow a sentence pair down to the words that actually changed.

    TartuNLP's `/v2` answers in whole sentences: `original` and `corrected` are
    both complete sentences, and only some words inside differ. Handing those
    straight to `_locate` highlighted **the entire sentence** as the mistake,
    which tells a learner nothing — the one thing a correction has to say is
    *which word*.

    Word-level common prefix and suffix, which is all that is needed: the two
    strings are the same sentence, so whatever is left in the middle after
    trimming the matching ends is the edit. Falls back to the whole pair when
    the trim leaves nothing on either side, so a pure insertion or deletion is
    still reported rather than silently dropped.
    """
    a, b = wrong.split(), right.split()
    head = 0
    while head < len(a) and head < len(b) and a[head] == b[head]:
        head += 1
    tail = 0
    while (tail < len(a) - head and tail < len(b) - head
           and a[len(a) - 1 - tail] == b[len(b) - 1 - tail]):
        tail += 1
    middle_a = " ".join(a[head:len(a) - tail])
    middle_b = " ".join(b[head:len(b) - tail])
    if not middle_a or not middle_b:
        return wrong, right
    # A shared trailing full stop rides along on the last word -- `autot.` for
    # `auto.` -- and highlighting a sentence's punctuation as the mistake is a
    # small lie about where the error is. Trim only what both sides share, so
    # a correction that *is* about punctuation still shows it.
    while (middle_a and middle_b and middle_a[-1] == middle_b[-1]
           and not middle_a[-1].isalnum() and len(middle_a) > 1 and len(middle_b) > 1):
        middle_a, middle_b = middle_a[:-1], middle_b[:-1]
    return middle_a, middle_b


def _tag_of(wrong: str, right: str) -> str:
    """The one tag this service's output actually supports claiming.

    TartuNLP returns no error type, so every correction used to be filed as
    `vocab` — which put word-order corrections and case corrections alike into
    the one bucket the error log uses for "wrong word", and the Notion log
    groups on this field.

    Exactly one type can be read off the strings themselves without inventing
    an annotation layer: if the correction only re-orders, the multiset of
    words is unchanged. That is the same signature `wordorder.is_reordering`
    already uses, imported rather than restated. Everything else stays `vocab`,
    which remains a guess and is left as the honest default.
    """
    from ..wordorder import is_reordering

    return "word-order" if is_reordering(wrong, right) else "vocab"


class TartuNLPGrammar:
    """TartuNLP's public GEC service at `api.tartunlp.ai/grammar`.

    **Status 2026-09-12: correct, and not answering.** A GET for their OpenAPI
    spec on this host returns in 0.65 s; a POST to either grammar endpoint
    hangs for 35 s with zero bytes; a POST to `translation/v2` on the *same
    host* returns in 0.85 s. That last probe is what rules out our network, the
    proxy and the request shape and leaves their worker. Their own demo at
    `grammar.tartunlp.ai` posts here too, and is down with it.

    So this class is a lane waiting on somebody else, not dead code: it starts
    answering the day they attach a worker, with no change here. The learner is
    insulated meanwhile — `PROVIDER_TIMEOUT` is 5 s split across the two
    endpoints, then the breaker opens for 900 s and backs off to six days.

    ## The contract, read from their spec rather than guessed

    `api.tartunlp.ai/grammar/openapi.json` is public and was fetched on
    2026-09-11. It publishes two endpoints, and this class now uses both:

    | Endpoint | Request | Answers with |
    |---|---|---|
    | `POST /grammar/v2` | `{"language": "et", "text": …}` | `corrections[{original, corrected, correction_log, explanations}]` — whole **sentences**, plus an Estonian-only explanation |
    | `POST /grammar/` | the same body | `corrections[{span:{start,end,value}, replacements:[{value}]}]` — exact character **spans** |

    ## Why both

    `/v2` is tried first because it is the only one that carries an
    explanation. `/` is tried when `/v2` fails, and it is not a consolation
    prize: it returns the character offsets this app otherwise has to recover
    by searching the text, and it skips the explanation step, so it is the
    cheaper of the two on their side and the likelier of the two to answer.

    ## What is actually wrong with it, measured 2026-09-11

    Nothing on this side. The request shape above matches their published
    schema exactly, the spec declares no authentication, and **both** endpoints
    answer **HTTP 500 after ~61 seconds** — reproduced with TartuNLP's own
    example string, `{"text": "Aitähh!"}`, which is the example printed in
    their spec. A `GET` returns 405, so the route exists and the host is up;
    only a `POST` reaches the worker that is not answering. That 405 is the
    trap worth naming: a liveness check that issues a `GET` goes green on a
    service that has never once returned a correction.

    So the short timeout stays, and the breaker stays. The 61-second failure
    must never be inflicted on someone waiting to see their mistake.
    """

    name = "tartunlp"

    #: `/v2` first for the explanation, then the span endpoint. Derived from
    #: the configured base so a change of host moves both.
    ENDPOINTS = (TARTUNLP_GRAMMAR, TARTUNLP_GRAMMAR.rsplit("/", 1)[0] + "/")

    def __init__(self, timeout: float = PROVIDER_TIMEOUT):
        self.timeout = timeout

    def available(self) -> bool:
        return os.environ.get("EESTI_DISABLE_TARTUNLP") != "1"

    def _post(self, url: str, text: str, timeout: float | None = None) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps({"language": "et", "text": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            return json.loads(resp.read())

    @staticmethod
    def _from_v2(payload: dict) -> list[Correction]:
        """Sentence pairs — narrowed to the words that changed."""
        out = []
        for entry in payload.get("corrections", []):
            original, corrected = entry.get("original", ""), entry.get("corrected", "")
            if not original or original == corrected:
                continue
            wrong, right = _minimal_span(original, corrected)
            out.append(Correction(
                wrong=wrong,
                correct=right,
                # Explanations come back in Estonian only; label them so the
                # learner is not surprised by the language switch.
                why=(entry.get("explanations") or "").strip() or "(selgitus puudub)",
                tag=_tag_of(original, corrected),
            ))
        return out

    @staticmethod
    def _from_v1(payload: dict) -> list[Correction]:
        """Spans and replacements — already the exact words, already located."""
        out = []
        for entry in payload.get("corrections", []):
            span = entry.get("span") or {}
            wrong = span.get("value") or ""
            replacements = [
                r.get("value") for r in (entry.get("replacements") or [])
                if isinstance(r, dict) and r.get("value")
            ]
            if not wrong or not replacements or replacements[0] == wrong:
                continue
            out.append(Correction(
                wrong=wrong,
                correct=replacements[0],
                why="(selgitus puudub)",
                tag=_tag_of(wrong, replacements[0]),
                start=span.get("start"),
                end=span.get("end"),
            ))
        return out

    def check(self, text: str) -> GrammarResult:
        """Two endpoints, one budget.

        `self.timeout` is the whole allowance for this provider, not the
        allowance per attempt. Spending it twice would double the wait on the
        chain's first provider — the one documented to answer 500 after 61 s —
        from 5 seconds to 10, against a docstring that says the short timeout
        exists precisely so that wait is never inflicted on someone waiting to
        see their mistake. Adding a fallback is not a licence to spend more of
        the learner's time; it is a second thing to try inside the same budget.
        """
        v2, root = self.ENDPOINTS
        half = self.timeout / 2
        try:
            return GrammarResult(
                self.name, _locate(text, self._from_v2(self._post(v2, text, half)))
            )
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                OSError, ValueError):
            # The span endpoint is a different code path on their side, and it
            # does not run the explanation step. Worth one attempt before the
            # chain gives up on Estonian-specific correction entirely.
            located = self._from_v1(self._post(root, text, half))
            # `_locate` only fills offsets it does not already have.
            return GrammarResult(
                self.name,
                [c if c.start is not None else _locate(text, [c])[0] for c in located],
            )


class LLMGrammar:
    """LLM checker, prompted for this learner's gap and the fixed Notion tags.

    Primary engine in practice: the only option that explains in Russian and can
    assign tags that group with the existing error log.

    Works against any OpenAI-compatible provider (EstLLM on Hugging Face or a
    local server, OpenRouter, Groq, Workers AI) so the deployment target can
    change without touching this class.
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
        from ..morph import object_case_candidates

        # `spelling()` rather than a second copy of the same loop, and located.
        #
        # This built its own unlocated `Correction`s, so every misspelling this
        # provider reported arrived with `start`/`end` of `None` and the page
        # had nothing to highlight. It went unnoticed because the offline
        # provider only answers when everything else has failed — and then
        # survived the merge, because a word this provider already named is the
        # one the merge keeps, so the *located* copy lost to the unlocated one.
        corrections = spelling(text)

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
                "любого провайдера: HF_TOKEN, OPENROUTER_API_KEY, "
                "GROQ_API_KEY или CLOUDFLARE_API_TOKEN."
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
# `huggingface` is second, and it is the same argument rather than a new one:
# that lane runs the *same* Estonian-adapted model as `local`, hosted. What
# separates them is who pays and who can read the request -- not the model. So
# every general-purpose lane stays behind both.
#
# This entry is also the reason the rule below exists. `huggingface` was once in
# `PROVIDERS` and never in this tuple: defined, unreachable, and unnoticed for
# exactly that reason. Anything added to `PROVIDERS` and not to this tuple is
# dead weight; a test asserts the two agree, which is what forced this line to
# be edited when the provider came back.
LLM_PREFERENCE = ("local", "huggingface", "openrouter", "groq", "workers-ai")


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


def why_failed(exc: BaseException) -> str:
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

    Public, and read by `eesti/evals/` too. The eval tracks rendered
    `type(exc).__name__` instead and so reported the same 400 as a bare
    `HTTPError` — the exact loss of the provider's own diagnosis that this
    function was written to stop, in the one place a person goes looking for
    why a model scored nothing.
    """
    if isinstance(exc, urllib.error.HTTPError):
        code = _error_code(exc)
        return f"HTTPError {exc.code} ({code})" if code else f"HTTPError {exc.code}"
    return type(exc).__name__


#: Russian, like every explanation the learner has to act on. Names the
#: authority, because "not in the dictionary" from Vabamorf is a different kind
#: of claim from "I think this is wrong" from a model, and the learner should
#: be able to tell them apart.
SPELLING_WHY = (
    "Слова нет в словаре Vabamorf. Проверь написание — чаще всего это "
    "пропущенная täpitäht: **õ ä ö ü**."
)


def spelling(text: str) -> list[Correction]:
    """Deterministic spelling, from Vabamorf's dictionary. No network, no model.

    Separated from `VabamorfFallback` so it can run **beside** whatever the
    chain answered rather than only when everything else has failed.
    """
    from ..morph import misspellings

    return _locate(text, [
        Correction(
            wrong=item["text"],
            correct=(item["suggestions"] or [""])[0],
            why=SPELLING_WHY,
            tag="vocab",
        )
        for item in misspellings(text)
    ])


#: Russian, like every explanation the learner acts on, keeping the Estonian
#: grammatical term so it can be looked up — the language rule in CLAUDE.md.
AGREEMENT_WHY = (
    "**Pöördelõpp** не совпадает с подлежащим: «{pronoun}» требует формы "
    "«{correct}». В эстонском лицо и число всегда видны на глаголе, а в "
    "русском — не всегда, поэтому эту ошибку легко не заметить."
)


def agreement(text: str) -> list[Correction]:
    """Subject–verb agreement, decided by morphology alone.

    The one syntactic error class this project can check *without* syntax:
    `ma elab` is wrong for a reason visible entirely in two adjacent words, and
    no context makes it right. So unlike object case, this is corrected rather
    than merely reported — and the correction is synthesised by the same
    Vabamorf that grades every drill.

    Rules and, more importantly, the exceptions come from GiellaLT's Estonian
    Constraint Grammar (`&err-agr`). See `morph.agreement_errors`.
    """
    from ..morph import agreement_errors

    return [
        Correction(
            wrong=item.verb,
            correct=item.correct,
            why=AGREEMENT_WHY.format(pronoun=item.pronoun, correct=item.correct),
            tag="verb-form",
            start=item.start if item.start >= 0 else None,
            end=item.end if item.end >= 0 else None,
        )
        for item in agreement_errors(text)
        if item.correct
    ]


#: Russian, keeping EKK's own frame words so the learner meets the form the
#: handbook uses — `millega`, not "the comitative".
#: Deliberately "рекомендует", not "требует" — the same hedge, for the same
#: reason, as the V2 explanation two constants up.
#:
#: Audited 2026-09-12 against EKI's current ühendsõnastik, one word at a time:
#: for **7 of the 23** contrasts (baseeruma, kaasuma, panustama, põhinema,
#: rajanema, sarnanema, tuginema) Sõnaveeb lists the form SÜ 64 stars as an
#: error among that word's attested rections. EKI's advice channel still
#: recommends what the handbook says — `põhinema millel`, `toetuma`/`tuginema`
#: millele — so the teaching is right and unchanged. What is not right is
#: calling the other form simply wrong when EKI's own dictionary records it:
#: that is the `-le` drift Emakeele Selts has a paper about, and describing a
#: strong recommendation as a requirement teaches a harder rule than EKI
#: states. The exam marks by the recommendation, so the recommendation is what
#: the learner is given — as a recommendation.
RECTION_WHY = (
    "**Rektsioon.** «{headword}» — EKI рекомендует **{correct}** "
    "({correct_frame}), а не **{wrong}** ({wrong_frame}). Это одна из ошибок, "
    "которые EKK перечисляет отдельно (SÜ 64): русский предлог и эстонский "
    "падеж здесь не совпадают, и форму на **-le** носители тоже иногда "
    "пишут — но на экзамене оценивают по рекомендации."
)


def rection(text: str) -> list[Correction]:
    """Attested rection confusions, from EKK's own list of the ones people miss.

    The second-largest error class in the learner corpus — 5 170 marks against
    object case's 653 — and checkable for one reason: EKK SÜ 64 does not
    describe valency, it lists **specific confusions**. Not "kohanema takes the
    comitative" but "people write `millele` where `millega` belongs". That is a
    lookup rather than a parse, which is why it can be done here at all.

    Degrades to nothing when the word list is absent: the contrasts live in it,
    an enrichment is never worth an error, and a fresh checkout has no database.
    """
    from .. import rection as ekk
    from ..wordlist import available, connect

    try:
        if not available():
            return []
        stored = ekk.load(connect())
    except Exception:  # noqa: BLE001 - a missing table is not a failed check
        return []

    return [
        Correction(
            wrong=item.wrong,
            correct=item.correct,
            why=RECTION_WHY.format(
                headword=item.headword, correct=item.correct,
                correct_frame=item.correct_frame, wrong=item.wrong,
                wrong_frame=item.wrong_frame),
            tag="rektsioon",
            start=item.start if item.start >= 0 else None,
            end=item.end if item.end >= 0 else None,
        )
        for item in ekk.errors(text, stored)
    ]


def _merge_spelling(text: str, result: GrammarResult) -> GrammarResult:
    """Add what the dictionary knows to what the provider said.

    **A dictionary lookup is code, and code does not lose to a model's
    opinion.** That is this project's central rule, and the chain was breaking
    it by accident: `check()` returns the *first* provider that answers, so the
    moment an LLM lane was configured it answered and Vabamorf's spelling
    verdict was thrown away — for every request, for ever.

    And the LLM will not cover for it. The prompt it ships with is aimed at
    object case and says in as many words that most text is already correct and
    to report a correction only where a rule above is broken. `tanav` for
    `tänav` breaks none of those rules, so nothing in the chain reported the
    single commonest way a Russian speaker mistypes Estonian: a missing
    täpitäht.

    The same argument carries **subject–verb agreement**, added alongside it:
    `ma elab` is decidable from morphology, Vabamorf can synthesise the form
    that belongs there, and no model needs to be asked. Both are evidence, not
    opinion, so both are merged rather than raced.

    Merged, not prepended: a word the provider already has something to say
    about keeps the provider's explanation, because that one has a reason
    attached and this one only has "not in the dictionary".
    """
    if not result.corrections and result.engine == "none":
        # Nothing answered at all. `check()` reports that honestly rather than
        # dressing a spellcheck up as a working grammar service.
        return result

    already = {c.wrong.casefold() for c in result.corrections if c.wrong}
    extra = [
        c for c in spelling(text) + agreement(text) + rection(text)
        if c.wrong.casefold() not in already
    ]
    if not extra:
        return result
    return GrammarResult(
        result.engine,
        result.corrections + extra,
        degraded=result.degraded,
        note=result.note,
    )


def check(text: str, providers: list[GrammarProvider] | None = None) -> GrammarResult:
    """Run the chain, returning the first provider that answers.

    Failures are expected, not exceptional, so they are swallowed and recorded in
    the final result's note rather than raised.

    Whatever answers, Vabamorf's spelling verdict is merged into it — see
    `_merge_spelling`.
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
            return _merge_spelling(text, result)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            _record_failure(provider.name)
            tried.append(f"{provider.name}: {why_failed(exc)}")
        except Exception as exc:  # bad JSON, SDK errors — never fatal
            _record_failure(provider.name)
            tried.append(f"{provider.name}: {why_failed(exc)}")

    return GrammarResult("none", [], degraded=True, note="; ".join(tried))
