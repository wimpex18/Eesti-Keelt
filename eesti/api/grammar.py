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
from .deps import db, gloss_db

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


def _meaning(simple, kept, native_offline=None) -> dict:
    """Which definition the card shows, and whose words it is.

    EKI's learner-level wording where there is one, Sõnaveeb's otherwise, with
    Sõnaveeb's kept alongside rather than replaced. The two live in different
    databases -- reference data in the image, learner data in the snapshot --
    so this is the one place they are read together and the preference is
    stated once.

    `definition_source` is the point of the function. The card renders EKI's
    text verbatim, and CC BY 4.0 asks that the reference to EKI be kept
    wherever the material is presented; a page cannot credit a source it cannot
    name. It was inferable from `full_definition` being non-null, which is a
    side effect rather than a statement -- and that inference was wrong in one
    real case: PSV has entries carrying examples and no definition, and the old
    expression returned `None` for those instead of falling back to Sõnaveeb's
    wording. Asking which source answered, rather than deducing it, fixes both.
    """
    psv_definition = simple.definition if simple else None
    native = kept.definition if kept else None
    # Third and last: EKI's native-level dictionaries (VSL, EKSS), offline, for
    # when Sõnaveeb had nothing or could not be asked. `(source id, text)`.
    offline_source, offline = native_offline or (None, None)
    definition = psv_definition or native or offline
    return {
        "definition": definition,
        # Named, not inferred. `None` when no source had anything to say.
        "definition_source": (
            "eki-psv" if psv_definition else "sonapi" if native
            else offline_source if offline else None),
        # Only when EKI answered and Sõnaveeb had something else to add, so the
        # card can offer the fuller wording without repeating itself.
        "full_definition": native if psv_definition and native != definition
                           else None,
        # `[]` until 2026-09-11, hardcoded — a field the API promised and no
        # source ever filled. PSV is the only source that has examples.
        "examples": list(simple.examples) if simple else [],
    }


def _russian(word: str, kept) -> dict:
    """The Russian on the card, and whose it is.

    **Offline EVS first, live Sõnaveeb second, EKI's education terms (HAR)
    last** — the same shape as the definition beside it (PSV, Sõnaveeb, then
    EKI's native-level dictionaries). EKI's Estonian–Russian
    dictionary is in the image and answers for ~60 000 lemmas with no request,
    no daily budget and no outage; Sõnaveeb's gloss is the fallback for what it
    lacks. Each stays in its own table (`evs_gloss`, `word_gloss`) and neither
    ever writes the other, so the preference is stated here and nowhere else.
    `russian_source` is named for the same CC BY reason as `definition_source`.
    """
    from ..evs import russian as evs_russian

    offline = evs_russian(db(), word)
    if offline:
        return {"russian": list(offline[:3]), "russian_source": "eki-evs"}
    if kept is not None and kept.russian:
        return {"russian": list(kept.russian[:3]), "russian_source": "sonapi"}
    from ..har import russian as har_russian

    terms = har_russian(db(), word)
    if terms:
        return {"russian": list(terms), "russian_source": "eki-har"}
    return {"russian": [], "russian_source": None}


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
    from ..psv import lookup as psv_lookup

    kept = gloss.remember(gloss_db(), word)
    # PSV covers ~6 000 basic words and is absent on a deployment that never
    # imported it; both are ordinary, so this never gates the response.
    simple = psv_lookup(db(), word)
    from ..ekidefs import lookup as native_offline

    meaning = _meaning(simple, kept, native_offline(db(), word))
    russian = _russian(word, kept)
    if kept is None or not kept.found:
        # Found if *any* source had something to show. The card draws nothing
        # when this is false, so counting only PSV hid every VSL definition
        # and every EVS gloss for a word Sõnaveeb does not know.
        shown = meaning["definition"] or meaning["examples"] or russian["russian"]
        return {"word": word, "found": bool(shown), **meaning, **russian}
    return {
        "word": word,
        "found": True,
        "governs": [p.strip() for p in (kept.rection or "").split(",") if p.strip()],
        "inflection_type": kept.inflection_type,
        **meaning,
        # The language policy says explanations are in Russian, and the API has
        # carried Russian glosses all along — under the per-meaning key the
        # module never read. Three at most: a word card is a reminder, not an
        # entry. EKI's dictionary first; see `_russian`.
        **russian,
        # The dictionary this app deliberately does not rebuild. Sõnaveeb has
        # the full paradigm, audio, and every translation; sending the learner
        # there is the honest answer to "I want more than three fields", and it
        # costs one link rather than a scraper the maintainers asked us not to
        # write.
        "sonaveeb": sonapi.entry_url(kept.lemma),
    }
