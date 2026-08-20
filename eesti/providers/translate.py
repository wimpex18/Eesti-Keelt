"""Sentence translation, from the one Estonian-specific service that stayed up.

## Why this exists at all

The app can already say what a *word* means: `gloss.py` keeps Sõnaveeb's Russian
glosses per lemma. It could not say what a *sentence* means, and those are not
the same problem. A reader stuck on `Neist 52 on kasvatatud Eestis` knows every
word in it and still cannot parse the clause; a learner drilling the partitive of
`süütamine` needs the sentence, not the headword.

## Why TartuNLP rather than an LLM

Three reasons, in order of how much they matter:

1. **It is built for Estonian.** The University of Tartu's NMT models are trained
   on Estonian, not on 119 languages of which Estonian is one. The eval in
   `docs/ai-strategy.md` is the whole argument: a 120B general model scored
   0.50/0.50 on Estonian object case. Translation is a narrower task, but the
   asymmetry is the same one.
2. **It has never been down.** The grammar endpoint on the same host has failed
   every probe since the first research round, including 2026-08-20. Translation
   answered in 1.0 s on that same run and on every one before it. That split —
   research *inference* is fragile, research *translation and TTS* are not — is
   the finding this project's whole provider design is built on.
3. **It costs nothing and needs no key.** No quota to exhaust, so nothing here
   competes with the grammar chain for OpenRouter's free tier.

## What it deliberately does not do

Translation is a **crutch, offered on request**. It is never shown beside a text
by default, because a reader who is handed Russian will read the Russian: the
comprehensible-input case for this app rests on the learner working at the edge
of what they understand, not past it. `/api/translate` exists so the crutch is
there when a sentence genuinely blocks; nothing calls it automatically.

It is also not a grader. Nothing about a translation feeds the drill loop, the
review queue or the readiness verdict — those stay deterministic, and a machine
translation is evidence about a model, not about the learner.
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


def translate(text: str, target: str = "rus",
              timeout: float | None = None) -> Translation | None:
    """One sentence in, one translation out. None if the service cannot answer.

    None rather than an exception: this is a crutch, and a crutch that raises
    is worse than one that is quietly absent for a minute.
    """
    text = (text or "").strip()
    if not text or target not in LANGUAGES:
        return None
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    request = urllib.request.Request(
        TARTUNLP_TRANSLATE,
        data=json.dumps({"text": text, "src": "est", "tgt": target}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(
            request, timeout=timeout or PROVIDER_TIMEOUT
        ) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None

    # The API returns a bare string for a single input and a list for a batch.
    result = payload.get("result")
    if isinstance(result, list):
        result = " ".join(str(r) for r in result)
    if not result or not str(result).strip():
        return None
    return Translation(source=text, text=str(result).strip(), target=target)
