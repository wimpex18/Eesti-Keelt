"""Grammar checking, as a chain of interchangeable providers.

Explaining LLM lanes, public GEC, Neurotõlge, then offline Vabamorf evidence.
Every result names its engine; fluent explanations do not confer authority.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field, replace
from typing import Protocol

from ..config import PROVIDER_TIMEOUT, TAGS, TARTUNLP_GRAMMAR, TARTUNLP_TRANSLATE
from . import breaker, budget

# The object-case rules and "most text is already correct" are stated positively
# here, as in the eval prompt (`evals/gec.py`): a model otherwise flags correct
# genitives, and a checker that invents errors is worse than none. The eval's
# worked examples are not copied: this prompt adds a Russian `why` field they
# would contradict.
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
    #: Who stands behind this correction (`verify`):
    #:
    #: - `deterministic` — code decided it (Vabamorf's dictionary, agreement,
    #:   EKK's rection list). It can be trusted and logged.
    #: - `model+verified` — a model proposed it and code checked what it could:
    #:   the suggested form is a word Vabamorf knows, and an object-case swap
    #:   agrees with the rules.
    #: - `model-only` — nothing code can check. Shown, never recorded.
    source: str = "model-only"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GrammarResult:
    engine: str
    corrections: list[Correction] = field(default_factory=list)
    degraded: bool = False
    #: For the learner, in Russian: shown in the writing banner.
    note: str = ""
    #: For the operator: which lanes were tried and how each failed
    #: (`llm:nvidia: HTTPError 410 (no-code)`). English; read by the smoke
    #: workflow, never shown to the learner.
    diagnostics: str = ""
    # True for a speech transcript: the recogniser may have introduced the "error".
    # Advisory results are shown and never recorded (no Notion log, no review queue).
    advisory: bool = False

    def to_dict(self) -> dict:
        return {
            "engine": self.engine,
            "degraded": self.degraded,
            "advisory": self.advisory,
            "note": self.note,
            "diagnostics": self.diagnostics,
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
        located.append(replace(c, start=start if start >= 0 else None, end=end))
    return located


def _minimal_span(wrong: str, right: str) -> tuple[str, str]:
    """Narrow a sentence pair down to the words that actually changed.

    TartuNLP `/v2` answers whole sentences; trim the common word prefix and suffix
    so only the edited words are highlighted. Falls back to the whole pair when
    nothing is left, so insertions and deletions are still reported.
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
    # Trim a trailing full stop both sides share; punctuation that did change stays.
    while (middle_a and middle_b and middle_a[-1] == middle_b[-1]
           and not middle_a[-1].isalnum() and len(middle_a) > 1 and len(middle_b) > 1):
        middle_a, middle_b = middle_a[:-1], middle_b[:-1]
    return middle_a, middle_b


def _tag_of(wrong: str, right: str) -> str:
    """The one tag this service's output supports: `word-order` when the correction
    only re-orders words (`wordorder.is_reordering`), otherwise `vocab`.
    """
    from ..wordorder import is_reordering

    return "word-order" if is_reordering(wrong, right) else "vocab"


class GECUnavailable(OSError):
    """Both endpoints failed; carries safe status identifiers, never bodies."""


class TartuNLPGrammar:
    """TartuNLP's public GEC service at `api.tartunlp.ai/grammar`.

    Contract from their published OpenAPI spec (no authentication):

    | Endpoint | Request | Answers with |
    |---|---|---|
    | `POST /grammar/v2` | `{"language": "et", "text": …}` | whole corrected sentences, plus an Estonian explanation |
    | `POST /grammar/` | the same body | exact character spans with replacements |

    `/v2` is tried first for the explanation, `/` when it fails. The service is
    often unresponsive (POSTs hang or return 500 while GET answers 405), so both
    share the short `PROVIDER_TIMEOUT` and the breaker skips it after failures.
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
            payload = json.loads(resp.read())
        self.validate(payload, v2=url.endswith('/v2'))
        return payload

    @staticmethod
    def validate(payload: dict, *, v2: bool) -> None:
        """An error object or incompatible schema must not mean 'no errors'."""
        if not isinstance(payload, dict) or not isinstance(payload.get("corrections"), list):
            raise ValueError("invalid GEC corrections")  # noqa: TRY004 - incompatible remote schema
        for entry in payload["corrections"]:
            if not isinstance(entry, dict):
                raise ValueError("invalid GEC correction")  # noqa: TRY004 - incompatible remote schema
            if v2:
                if not all(isinstance(entry.get(k), str) for k in ("original", "corrected")):
                    raise ValueError("invalid GEC sentence pair")
            elif (not isinstance(entry.get("span"), dict)
                  or not isinstance(entry.get("replacements"), list)):
                raise ValueError("invalid GEC span")

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
        """Split the socket timeout across endpoints; connection overhead is extra."""
        v2, root = self.ENDPOINTS
        half = self.timeout / 2
        try:
            return GrammarResult(
                self.name, _locate(text, self._from_v2(self._post(v2, text, half)))
            )
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                OSError, ValueError) as first:
            # The span endpoint is a different code path on their side, and it
            # does not run the explanation step. Worth one attempt before the
            # chain gives up on Estonian-specific correction entirely.
            first_reason = why_failed(first)
            try:
                located = self._from_v1(self._post(root, text, half))
            except (OSError, ValueError) as second:
                raise GECUnavailable(
                    f"v2={first_reason}; spans={why_failed(second)}") from None
            # `_locate` only fills offsets it does not already have.
            return GrammarResult(
                self.name,
                [c if c.start is not None else _locate(text, [c])[0] for c in located],
            )


#: Words that make a missing object partitive whatever the aspect (EKK: eitus).
NEGATION = frozenset({"ei", "ära", "ärge", "pole", "polnud", "mitte"})


class NeurotolgeCorrection:
    """TartuNLP's translation service run Estonian → Estonian, as a corrector.

    Neurotõlge normalises what it is given, so `est→est` hands back a corrected
    sentence (`ostin piim` → `ostsin piima`). It also paraphrases: it reorders
    words and drops some (`läbi`), which is not a correction. So only edits code
    can vouch for are kept:

    - a one-for-one word substitution (no insertion, deletion or reordering);
    - both words analyse to a shared Vabamorf lemma, so only the form changed;
    - singular ↔ plural changes are dropped: as often a paraphrase as a fix;
    - a genitive ↔ partitive swap is an aspect judgement Neurotõlge cannot be
      trusted with, and is kept only when a negation makes partitive obligatory.

    It explains nothing; the `why` says so. The service stores what it is sent
    (TartuNLP's terms), which `docs/ai-providers.md` states.
    """

    name = "tartunlp-mt"

    def __init__(self, timeout: float = PROVIDER_TIMEOUT):
        self.timeout = timeout

    def available(self) -> bool:
        return os.environ.get("EESTI_DISABLE_TARTUNLP") != "1"

    def _normalised(self, text: str) -> str:
        req = urllib.request.Request(
            TARTUNLP_TRANSLATE,
            data=json.dumps({"text": text, "src": "est", "tgt": "est"}).encode(),
            # TartuNLP asks integrators to name themselves.
            headers={"Content-Type": "application/json", "application": "eesti-keelt"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            result = json.loads(resp.read()).get("result")
        if isinstance(result, list):
            result = " ".join(str(r) for r in result)
        if not isinstance(result, str) or not result.strip():
            raise ValueError("empty normalisation")
        return result.strip()

    @staticmethod
    def _words(text: str) -> list[str]:
        return re.findall(r"[\wÕÄÖÜõäöüŠŽšž-]+", text)

    @staticmethod
    def _object_swap(wrong_forms: set[str], right_forms: set[str]) -> str | None:
        """'to-partitive' / 'to-genitive' when the edit swaps object case, else None."""
        part = {"sg p", "pl p"}
        gen = {"sg g", "pl g"}
        if wrong_forms & gen and right_forms & part and not wrong_forms & part:
            return "to-partitive"
        if wrong_forms & part and right_forms & gen and not right_forms & part:
            return "to-genitive"
        return None

    def verified(self, text: str, normalised: str) -> list[Correction]:
        """The edits between `text` and `normalised` that code can vouch for."""
        import difflib

        from ..morph import _readings

        a, b = self._words(text), self._words(normalised)
        negated = any(w.casefold() in NEGATION for w in a)
        out: list[Correction] = []
        matcher = difflib.SequenceMatcher(a=[w.casefold() for w in a],
                                          b=[w.casefold() for w in b], autojunk=False)
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op != "replace" or (i2 - i1) != (j2 - j1):
                continue
            for wrong, right in zip(a[i1:i2], b[j1:j2]):
                ra, rb = _readings(wrong), _readings(right)
                lemmas = {lemma for lemma, _ in ra} & {lemma for lemma, _ in rb}
                if not rb or not lemmas:
                    continue
                fa, fb = {f for _, f in ra}, {f for _, f in rb}
                # Singular ↔ plural is a paraphrase as often as a fix
                # (`kodutööd` → `kodutöid`): keep only edits whose readings have
                # the same numbers, so an ambiguous form cannot slip through.
                na = {f.split()[0] for f in fa if f[:2] in ("sg", "pl")}
                nb = {f.split()[0] for f in fb if f[:2] in ("sg", "pl")}
                if na and nb and na != nb:
                    continue
                swap = self._object_swap(fa, fb)
                if swap == "to-genitive" or (swap == "to-partitive" and not negated):
                    continue
                lemma = sorted(lemmas)[0]
                out.append(Correction(
                    wrong=wrong, correct=right,
                    source="model+verified",
                    why=(f"Neurotõlge (est→est) предлагает другую форму слова «{lemma}». "
                         "Объяснения этот сервис не даёт — сверь с правилом."
                         if swap is None else
                         "После отрицания (eitus) дополнение стоит в osastav."),
                    tag="obj-case" if swap else "vocab",
                ))
        return _locate(text, out)

    def check(self, text: str) -> GrammarResult:
        return GrammarResult(
            self.name, self.verified(text, self._normalised(text)),
            note="Исправления без объяснений: Neurotõlge правит форму, но не "
                 "говорит почему. Правило смотри по ссылке.")


class LLMGrammar:
    """LLM checker, prompted for this learner's gap and the fixed Notion tags.

    The only engine that explains in Russian and assigns tags that group with the
    error log. Works with any lane in `llm.PROVIDERS`; compare lanes with
    `python -m eesti.cli eval --provider X` before reordering.
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
            complete(self.provider_name, SYSTEM_PROMPT, text, model=self.model, attempts=1)
        )
        if (not isinstance(payload, dict) or not isinstance(payload.get("corrections"), list)
                or any(not isinstance(c, dict)
                       or not all(isinstance(c.get(key), str) for key in ("wrong", "correct", "why"))
                       for c in payload["corrections"])):
            raise ValueError("invalid grammar response schema")
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

    It cannot decide whether a partitive should have been genitive (that needs
    telicity); it reports the case written and misspellings, and says so.
    """

    name = "vabamorf-offline"

    def available(self) -> bool:
        return True

    def check(self, text: str) -> GrammarResult:
        from ..morph import object_case_candidates

        # Located spelling corrections from `spelling()`, so the page can highlight them.
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
                # Evidence, not a verdict: the case written, for the learner to
                # judge. Code produced it, so it is not a model's claim.
                source="deterministic",
                start=t.start,
                end=t.end,
            )
            for t in object_case_candidates(text)
        ]

        return GrammarResult(
            self.name,
            corrections + flagged,
            degraded=True,
            note=_offline_note(),
        )


#: The keys that turn on a lane able to explain a correction.
EXPLAINING_KEYS = ("CLOUDFLARE_API_TOKEN", "MISTRAL_API_KEY", "OPENROUTER_API_KEY")


def _offline_note() -> str:
    """What the learner reads when only the offline check answered: fix a key
    only when none is set; otherwise the services did not answer."""
    base = "Офлайн-режим: показаны кандидаты на obj-case и опечатки, но без проверки правильности."
    if any(os.environ.get(k) for k in EXPLAINING_KEYS):
        return base + " Сервисы разбора сейчас не ответили — попробуй ещё раз позже."
    return (base + " Для полного разбора задай ключ любого провайдера: "
            + ", ".join(EXPLAINING_KEYS[:-1]) + " или " + EXPLAINING_KEYS[-1] + ".")


# Tags a transcript cannot support: `vocab` on a transcript is usually the
# recogniser inventing a word, not a learner's spelling mistake.
SPEECH_UNSUPPORTED_TAGS = frozenset({"vocab"})


def unrecognised_words(text: str) -> set[str]:
    """Tokens Vabamorf does not know — on a transcript, the recogniser's inventions."""
    from ..morph import misspellings

    return {item["text"].casefold() for item in misspellings(text)}


def from_transcript(result: "GrammarResult", text: str = "") -> "GrammarResult":
    """Re-read a written-text check as what it is when the input was spoken.

    A transcript mixes what was said with what was heard, so:

    1. Corrections anchored on a word Vabamorf does not recognise are dropped,
       whatever their tag (unknown words are recomputed from the text, so the rule
       holds for every engine).
    2. The rest is marked `advisory` and never reaches the Notion log or the
       review queue.
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
        diagnostics=result.diagnostics,
        degraded=result.degraded,
        advisory=True,
        note=(
            "Транскрипция речи: распознавание могло услышать не то, что ты "
            "сказал. Подсказки — не подтверждённые ошибки."
        ),
    )


#: LLM lanes in the order the chain tries them; unconfigured lanes are skipped.
#: `local` runs an Estonian-adapted model and is off unless LOCAL_LLM_URL is set.
#: Only evaluated, operational lanes belong in automatic grammar/tutor routing.
#: NVIDIA remains available to the CLI eval, pending recovery and re-evaluation.
LLM_PREFERENCE = ("local", "workers-ai", "mistral", "openrouter")


def build_chain(providers: list[GrammarProvider] | None = None) -> list[GrammarProvider]:
    """Explaining LLMs, bounded public GEC, Neurotõlge, then offline evidence.

    Public GEC has no demonstrated latency/quality advantage over the working
    LLM lane. Keep it as an optional fallback, not a delay on every first check.
    """
    if providers is not None:
        return providers
    return [
        *(LLMGrammar(name) for name in LLM_PREFERENCE),
        TartuNLPGrammar(),
        # Code-filtered corrections without explanations: after every lane that
        # explains, before the offline evidence.
        NeurotolgeCorrection(),
        VabamorfFallback(),
    ]


#: `non-json` and `no-code` stand in when a provider gives no identifier.
#:
#: An error identifier (`model_decommissioned`, `invalid_api_key`): no spaces,
#: capitals or non-ASCII, and short, so a learner's sentence can never match and a
#: response body never reaches the note.
_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_.-]{2,39}$")


def _error_code(exc: urllib.error.HTTPError) -> str:
    """The provider's own name for the failure, or "" if it did not give one.

    Reads `{"error": {"code"|"type": ...}}`; anything that is not an identifier
    (prose, proxy HTML, an echoed request) is dropped. Capped and never raises.
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
        # Not JSON: usually a proxy in front of the API (an HTML challenge page), which
        # is a different diagnosis from the API refusing.
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

    Includes the HTTP status and the provider's own error code: a 429 (wait), a
    401 (replace the key) and a 403 for a withdrawn model id are different jobs.
    Never a response body — the note reaches CI logs and the checked text is the
    learner's writing. Also used by `eesti/evals/`.
    """
    if isinstance(exc, GECUnavailable):
        return f"GECUnavailable ({exc})"
    if isinstance(exc, urllib.error.HTTPError):
        code = _error_code(exc)
        return f"HTTPError {exc.code} ({code})" if code else f"HTTPError {exc.code}"
    from .llm import EmptyReply

    if isinstance(exc, EmptyReply):
        # `finish_reason` is the API's identifier (`length`, `stop`), never prose.
        return f"empty reply ({exc.finish_reason})"
    return type(exc).__name__


#: Russian, naming the authority: "not in Vabamorf's dictionary" is a different
#: claim from a model's opinion.
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
            source="deterministic",
        )
        for item in misspellings(text)
    ])


#: Russian, like every explanation the learner acts on, keeping the Estonian
#: grammatical term so it can be looked up — the language rule in AGENTS.md.
AGREEMENT_WHY = (
    "**Pöördelõpp** не совпадает с подлежащим: «{pronoun}» требует формы "
    "«{correct}». В эстонском лицо и число всегда видны на глаголе, а в "
    "русском — не всегда, поэтому эту ошибку легко не заметить."
)


def agreement(text: str) -> list[Correction]:
    """Subject–verb agreement, decided by morphology alone.

    `ma elab` is wrong from two adjacent words, so this corrects rather than
    reports, with the form synthesised by Vabamorf. Rules and exceptions follow
    GiellaLT's Estonian Constraint Grammar (`&err-agr`); see
    `morph.agreement_errors`.
    """
    from ..morph import agreement_errors

    return [
        Correction(
            wrong=item.verb,
            correct=item.correct,
            why=AGREEMENT_WHY.format(pronoun=item.pronoun, correct=item.correct),
            tag="verb-form",
            source="deterministic",
            start=item.start if item.start >= 0 else None,
            end=item.end if item.end >= 0 else None,
        )
        for item in agreement_errors(text)
        if item.correct
    ]


#: Russian, keeping EKK's own frame words (`millega`, not "the comitative").
#: "рекомендует", not "требует": for 7 of the 23 contrasts EKI's current
#: dictionary also records the starred form, so the handbook's choice is taught as
#: a recommendation, which is what the exam marks.
RECTION_WHY = (
    "**Rektsioon.** «{headword}» — EKI рекомендует **{correct}** "
    "({correct_frame}), а не **{wrong}** ({wrong_frame}). Это одна из ошибок, "
    "которые EKK перечисляет отдельно (SÜ 64): русский предлог и эстонский "
    "падеж здесь не совпадают, и форму на **-le** носители тоже иногда "
    "пишут — но на экзамене оценивают по рекомендации."
)


def rection(text: str) -> list[Correction]:
    """Attested rection confusions from EKK SÜ 64's list of common mistakes.

    A lookup, not a parse: SÜ 64 lists specific confusions ("`millele` where
    `millega` belongs"). Returns nothing when the word list is absent.
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
            source="deterministic",
            start=item.start if item.start >= 0 else None,
            end=item.end if item.end >= 0 else None,
        )
        for item in ekk.errors(text, stored)
    ]


def verify(text: str, corrections: list[Correction]) -> list[Correction]:
    """Say what code can vouch for in each correction (`Correction.source`).

    Code cannot decide whether a model's rewrite is *right* — that is the whole
    reason a model was asked. It can decide whether the suggestion is Estonian
    at all, and whether an object-case swap agrees with the rules the app
    already owns. Everything else stays `model-only`: shown to the learner,
    never written to the error log or the review queue.
    """
    from ..morph import _readings

    out = []
    for c in corrections:
        if c.source == "deterministic":
            out.append(c)
            continue
        source = "model-only"
        wrong, right = c.wrong.strip(), (c.correct or "").strip()
        if right and " " not in right and " " not in wrong:
            known_right = bool(_readings(right))
            lemmas_right = {lemma for lemma, _ in _readings(right)}
            lemmas_wrong = {lemma for lemma, _ in _readings(wrong)}
            if known_right and (lemmas_wrong & lemmas_right or not lemmas_wrong):
                # A form of the same word, or a real word replacing one Vabamorf
                # does not know (a misspelling): both are checkable claims.
                source = "model+verified"
            # A provider's tag is not evidence: GEC calls these edits `vocab`.
            # Detect the morphology too, or a mistagged aspect judgement can
            # become a supposedly verified correction.
            object_swap = NeurotolgeCorrection._object_swap(
                {f for _, f in _readings(wrong)}, {f for _, f in _readings(right)})
            if source == "model+verified" and (c.tag == "obj-case" or object_swap):
                source = _verified_object_case(text, wrong, right)
        out.append(Correction(c.wrong, c.correct, c.why, c.tag, c.start, c.end,
                              source))
    return out


#: Where one clause ends and the next begins, for the negation test below.
_CLAUSE = re.compile(r"[,.;:!?]|\s(?:ja|ning|aga|kuid|vaid|et|sest)\s")


def _clause_around(text: str, word: str) -> str:
    """The clause the word sits in. A negation two clauses away governs nothing."""
    at = text.find(word)
    if at < 0:
        return text
    start = max((m.end() for m in _CLAUSE.finditer(text, 0, at)), default=0)
    end = next((m.start() for m in _CLAUSE.finditer(text, at + len(word))), len(text))
    return text[start:end]


def _verified_object_case(text: str, wrong: str, right: str) -> str:
    """An object-case swap is the app's documented weakness, so it is only
    `model+verified` where a rule decides it: after a negation **in the same
    clause** the object is partitive (EKK). Aspect is judgement, and stays
    `model-only` — which is exactly the call a model gets wrong.
    """
    from ..morph import _readings

    part = {"sg p", "pl p"}
    forms_right = {f for _, f in _readings(right)}
    clause = _clause_around(text, wrong)
    negated = any(w.strip(".,!?").casefold() in NEGATION for w in clause.split())
    if negated and forms_right & part:
        return "model+verified"
    return "model-only"


def _merge_spelling(text: str, result: GrammarResult) -> GrammarResult:
    """Add deterministic evidence to what the provider said.

    Spelling (Vabamorf's dictionary) and subject–verb agreement are code, and code
    does not lose to a model: `check()` returns the first provider that answers, so
    without this merge an LLM answer would discard them — and the LLM prompt does
    not cover a missing täpitäht. A deterministic finding replaces a model suggestion on the same word;
    the model cannot suppress or override the check.
    """
    if not result.corrections and result.engine == "none":
        # Nothing answered at all. `check()` reports that honestly rather than
        # dressing a spellcheck up as a working grammar service.
        return result

    extra = spelling(text) + agreement(text) + rection(text)
    if not extra:
        return result
    return GrammarResult(
        result.engine,
        [c for c in result.corrections
         if c.wrong.casefold() not in {e.wrong.casefold() for e in extra}] + extra,
        degraded=result.degraded,
        note=result.note,
        diagnostics=result.diagnostics,
    )


def check(text: str, providers: list[GrammarProvider] | None = None) -> GrammarResult:
    """Run the chain, returning the first provider that answers.

    Failures are expected and recorded in the result's diagnostics rather than
    raised. Deterministic checks are merged in (`_merge_spelling`).
    """
    tried: list[str] = []
    for provider in build_chain(providers):
        if not provider.available():
            tried.append(f"{provider.name}: unavailable")
            continue
        if _breaker_open(provider.name):
            tried.append(f"{provider.name}: skipped (recent failures)")
            continue
        if budget.exhausted(provider.name):
            # The day's allowance for this lane is spent; the next lane answers.
            tried.append(f"{provider.name}: skipped (day's budget spent)")
            continue
        try:
            budget.spend(provider.name)
            result = provider.check(text)
            result.corrections = verify(text, result.corrections)
            _record_success(provider.name)
            if tried:
                result.diagnostics = "skipped -> " + "; ".join(tried)
            return _merge_spelling(text, result)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            _record_failure(provider.name)
            tried.append(f"{provider.name}: {why_failed(exc)}")
        except Exception as exc:  # bad JSON, SDK errors — never fatal
            _record_failure(provider.name)
            tried.append(f"{provider.name}: {why_failed(exc)}")

    return GrammarResult(
        "none", [], degraded=True,
        note="Проверка сейчас недоступна — ни один сервис разбора не ответил. Попробуй позже.",
        diagnostics="; ".join(tried))
