"""Checking a sentence, and looking a word up.

The only two places a model is allowed near: it may explain a correction in
prose and translate, and it decides nothing about whether an answer is right.
See `docs/ai-boundaries.md`.
"""

from __future__ import annotations

import re

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

    TartuNLP's Estonian-trained translation does this job; it is free, keyless
    and reliable.

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


def _without(text: str | None, shown: str | None) -> str | None:
    """`text`'s definitions minus the one already on the card, or None.

    Sõnaveeb's mirror returns every definition of a word in one string, joined
    by a comma with no space — `tõesti` came back as "(päris)
    kindlasti,rõhutab, et miski on just nii, nagu sa ütled", the second half
    being PSV's own learner wording, which Sõnaveeb also carries. Prose puts a
    space after its commas, so the join is recoverable: split there, drop what
    the card already shows, and join the rest so the seam is visible.
    """
    if not text:
        return None
    parts = [p.strip() for p in re.split(r",(?=\S)", text) if p.strip()]
    kept = [p for p in parts if p != (shown or "").strip()]
    return "; ".join(kept) or None


def _fuller(learner_shown, definition, native, live_source, offline_source, offline) -> dict:
    native = _without(native, definition) if learner_shown else native
    if learner_shown and native and native != definition:
        return {"full_definition": native, "full_definition_source": live_source}
    if learner_shown and offline and offline != definition:
        return {"full_definition": offline, "full_definition_source": offline_source}
    return {"full_definition": None, "full_definition_source": None}


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
    # Learner-level wording first: Ekilex's `wwLite` definition — the
    # *Keeleõppija Sõnaveeb* text, maintained today — then PSV's 2014 snapshot
    # of it. Then the live native definition, then EKI's native-level files.
    live_source = getattr(kept, "source", None) or "sonapi"
    live_learner = getattr(kept, "learner_definition", None) if kept else None
    psv_definition = simple.definition if simple else None
    native = kept.definition if kept else None
    offline_source, offline = native_offline or (None, None)
    learner = live_learner or psv_definition
    definition = learner or native or offline
    return {
        "definition": definition,
        # Named, not inferred. `None` when no source had anything to say.
        "definition_source": (
            live_source if live_learner else "eki-psv" if psv_definition
            else live_source if native else offline_source if offline else None),
        # The native-level wording beside PSV's learner one: the live
        # dictionary's, else EKSS/VSL offline. Only when PSV answered and the
        # fuller text says something else, so the card never repeats itself.
        # The card shows it folded under "täpsem seletus".
        **_fuller(bool(learner), definition, native, live_source, offline_source, offline),
        # PSV is the only source that has examples.
        "examples": list(simple.examples) if simple else [],
    }


def _russian(word: str, kept) -> dict:
    """The Russian on the card, and whose it is — the order lives in `meaning.py`.

    `russian_source` is named for the same CC BY reason as `definition_source`.
    """
    from ..meaning import russian

    live_definition = bool(kept is not None and (getattr(kept, "learner_definition", None)
                                                  or kept.definition))
    found, source = russian(db(), word, kept.russian if kept is not None else (),
                            live_source=getattr(kept, "source", None) or "sonapi",
                            beside_its_definition=live_definition)
    return {"russian": found, "russian_source": source}


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
    from .. import evs, gloss
    from ..ekidefs import lookup as native_offline
    from ..providers import sonapi
    from ..psv import lookup as psv_lookup

    words = db()
    simple = psv_lookup(words, word)
    offline_type = evs.inflection_type(words, word)
    # The live dictionary is always asked — it is EKI's database as it is today,
    # where every downloaded file is a snapshot — through the store, so a word
    # is asked about once and never again, and within `gloss.DAILY_BUDGET`.
    # EKI's files fill what it leaves empty and answer when it cannot be asked.
    kept = gloss.remember(gloss_db(), word)
    live = kept if kept is not None and kept.found else None

    meaning = _meaning(simple, live, native_offline(words, word))
    russian = _russian(word, live)
    live_rection = [p.strip() for p in ((live.rection if live else "") or "").split(",") if p.strip()]
    governs = live_rection or list(simple.rection if simple else ())
    inflection_type = (live.inflection_type if live and live.inflection_type else None) or offline_type
    shown = (meaning["definition"] or meaning["examples"] or russian["russian"]
             or governs or inflection_type)
    return {
        "word": word,
        # Found if *any* source had something to show: the card draws nothing
        # when this is false.
        "found": bool(shown),
        "governs": governs,
        "governs_source": ((live.source if live else None) if live_rection
                           else "eki-psv" if governs else None),
        # Ekilex's CEFR level for the word's main sense, when Ekilex answered.
        "live_level": getattr(live, "level", None),
        "inflection_type": inflection_type,
        **meaning,
        # The language policy says explanations are in Russian. Three at most:
        # a word card is a reminder, not an entry. Whose Russian wins is
        # `meaning.py`'s call.
        **russian,
        # The dictionary this app deliberately does not rebuild — one link
        # rather than a scraper the maintainers asked us not to write.
        "sonaveeb": sonapi.entry_url(live.lemma if live else word),
    }
