"""Checking a sentence, and looking a word up.

The only two places a model is allowed near: it may explain a correction in
prose and translate, and it decides nothing about whether an answer is right.
See `docs/ai-boundaries.md`.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..lookup import lookup
from ..providers import grammar
from .deps import gloss_db

router = APIRouter()

class CheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


@router.post("/api/check")
def check(req: CheckRequest) -> dict:
    """Grammar check through the provider chain, plus what the text actually says.

    The back-translation is the addition, and it answers a question grammar
    checking structurally cannot. A checker tells you whether your Estonian is
    *well formed*. It cannot tell you whether it says what you meant — those
    are different failures, and for a learner the second is the more common and
    the more invisible one. Write `Ma käisin arsti juures` when you meant "I
    went to the doctor's" and every word is correct; write `Ma käisin arstiga`
    and it is still correct Estonian, and it now means you went *with* a doctor.
    No grammar chain flags that. Reading it back in Russian does.

    This is the one job an Estonian-trained NMT is better at than a general LLM,
    and it is free, keyless, and on the one TartuNLP endpoint that has never
    been down — measured again on 2026-08-20: translation answers in 1.0s while
    its grammar sibling on the same host returns 500 after 60.7s, unchanged
    since the first probe six months ago.

    Never blocking. If translation is unavailable the check returns exactly what
    it always did.
    """
    result = grammar.check(req.text).to_dict()

    from ..providers.translate import translate

    back = translate(req.text, target="rus")
    result["back_translation"] = back.text if back else None
    return result


@router.get("/api/lookup/{word}")
def lookup_word(word: str) -> dict:
    """Analyse one word: lemma, case, CEFR level, and its object-case pair."""
    return lookup(word)


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    target: str = "rus"


@router.post("/api/translate")
def translate_sentence(req: TranslateRequest) -> dict:
    """Translate one Estonian sentence, on request and never on its own.

    The endpoint the app has had configured since the first week and never
    called: `TARTUNLP_TRANSLATE` sat in `config.py` with no caller anywhere,
    which is the same defect as a measurement with no writer.

    It is worth having for the thing `gloss.py` cannot do. A word gloss says
    what `süütamine` means; it does not unpick `Neist 52 on kasvatatud Eestis`
    for someone who knows every word in it. Sentence-level help is a different
    tool and this is the free, Estonian-trained, keyless one.

    Deliberately a POST and deliberately not attached to anything that renders
    automatically. A reader handed Russian reads the Russian, and this app's
    whole reading design rests on working at the edge of what is understood
    rather than past it. The learner asks; nothing offers.
    """
    from ..providers.translate import translate

    got = translate(req.text, target=req.target)
    if got is None:
        # A crutch that is briefly absent, not an error page.
        return {"ok": False, "text": None,
                "detail": "Перевод сейчас недоступен — попробуйте ещё раз."}
    return {"ok": True, "text": got.text, "target": got.target,
            "engine": got.engine}


@router.get("/api/enrich/{word}")
def enrich_word(word: str) -> dict:
    """The two things Vabamorf cannot say: what the word governs, and its type.

    `providers/sonapi.py` has always existed for exactly this — its own
    docstring says it "enriches a word the learner is actually looking at" —
    and nothing had ever called it. Sixty-two statements, zero coverage, no
    importer: the module-level version of an endpoint with no caller.

    Rection is the `rektsioon` error tag directly: which case a verb governs is
    a list, not a rule, and no amount of morphology derives it. The
    inflection type is the muuttüüp the Notion "Nomenid A–F" page already
    tracks.

    Deliberately a **second** request rather than part of `/api/lookup`. This
    one leaves the machine, and a word card must not wait on a third party or
    disappear when one is down. An empty object is the honest answer to "the
    lookup did not come back", and the page simply adds nothing.
    """
    from .. import gloss
    from ..providers import sonapi

    # Through the store, so a word is asked about once and then never again.
    # `sonapi`'s own cache is on the container's disk, which Cloud Run throws
    # away every time it scales to zero -- so the module that promises not to
    # hammer Sõnaveeb was re-requesting the same words every session.
    kept = gloss.remember(gloss_db(), word)
    if kept is None or not kept.found:
        return {"word": word, "found": False}
    return {
        "word": word,
        "found": True,
        "governs": [p.strip() for p in (kept.rection or "").split(",") if p.strip()],
        "inflection_type": kept.inflection_type,
        "definition": kept.definition,
        "examples": [],
        # The language policy says explanations are in Russian, and the API has
        # carried Russian glosses all along — under the per-meaning key the
        # module never read. Three at most: a word card is a reminder, not an
        # entry.
        "russian": list(kept.russian[:3]),
        # The dictionary this app deliberately does not rebuild. Sõnaveeb has
        # the full paradigm, audio, and every translation; sending the learner
        # there is the honest answer to "I want more than three fields", and it
        # costs one link rather than a scraper the maintainers asked us not to
        # write.
        "sonaveeb": sonapi.entry_url(kept.lemma),
    }
