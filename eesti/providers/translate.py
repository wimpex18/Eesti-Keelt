"""Sentence translation via TartuNLP (Estonian-trained NMT, free, no key).

Word glosses cannot unpick a clause (`Neist 52 on kasvatatud Eestis`); this can.
TartuNLP rather than an LLM: it is built for Estonian and spends no
grammar-lane quota.

**Offered on request only**, never beside a text by default: a reader handed
Russian reads the Russian. **Not a grader:** nothing about a translation feeds
drills, review or readiness.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..config import PROVIDER_TIMEOUT, TARTUNLP_TRANSLATE

#: Three-letter codes, which is what this API takes. `est` in, `rus` out is the
#: pair this learner needs; `eng` is kept because a Russian gloss occasionally
#: lands on a word whose English is clearer.
LANGUAGES = ("rus", "eng")

#: A paragraph, not an essay. The endpoint accepts more, but a request the
#: learner is waiting on should be one sentence or a few.
MAX_CHARS = 1200


@dataclass(frozen=True)
class Translation:
    source: str
    text: str
    target: str
    engine: str = "tartunlp"


def result_text(payload: object) -> str | None:
    """Only translated strings count as answers, never an error object's repr."""
    if not isinstance(payload, dict):
        return None
    result = payload.get("result")
    if isinstance(result, list):
        if not all(isinstance(part, str) and part.strip() for part in result):
            return None
        result = " ".join(result)
    return result.strip() if isinstance(result, str) and result.strip() else None


def translate(text: str, target: str = "rus",
              timeout: float | None = None) -> Translation | None:
    """One sentence in, one translation out; None (not an exception) when the service
    cannot answer.
    """
    text = (text or "").strip()
    if not text or target not in LANGUAGES:
        return None
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    request = urllib.request.Request(
        TARTUNLP_TRANSLATE,
        data=json.dumps({"text": text, "src": "est", "tgt": target,
                         "application": "eesti-keelt"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(
            request, timeout=timeout or PROVIDER_TIMEOUT
        ) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None

    # The API returns a bare string for a single input and a list for a batch.
    result = result_text(payload)
    if result is None:
        return None
    return Translation(source=text, text=result, target=target)
