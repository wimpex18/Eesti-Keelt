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
    """Grammar check through the provider chain, plus a back-translation.

    A checker says whether the Estonian is well formed, not whether it says what
    was meant: `Ma käisin arstiga` is correct and means "with a doctor". Reading it
    back in Russian (TartuNLP translation) shows that. Never blocking: without
    translation the check returns as usual.
    """
    result = grammar.check(req.text).to_dict()

    from .. import evidence

    # Writing practice is evidence too: what was written, and what was found in it.
    evidence.record("writing", {
        "text": req.text, "words": len(req.text.split()),
        "engine": result["engine"], "degraded": result["degraded"],
        "corrections": [{"wrong": c["wrong"], "correct": c["correct"], "tag": c["tag"]}
                        for c in result["corrections"]],
    })

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
    """Translate one Estonian sentence, on request only (a POST the learner triggers),
    so reading stays at the edge of what is understood.
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
    """`text`'s definitions minus the one already on the card, or None. The Sõnaveeb
    mirror joins definitions with a comma and no space; split there.
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

    EKI's learner-level wording where there is one, otherwise the live dictionary's,
    with the native-level wording kept beside it. `definition_source` names the
    source so the card can credit EKI (CC BY 4.0). PSV entries with examples but no
    definition fall back to the live wording.
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
        # The native-level wording beside PSV's (live dictionary, else EKSS/VSL), only
        # when it differs; shown folded under "täpsem seletus".
        **_fuller(bool(learner), definition, native, live_source, offline_source, offline),
        # PSV is the only source that has examples.
        "examples": list(simple.examples) if simple else [],
    }


def _russian(word: str, kept) -> dict:
    """The Russian on the card and whose it is (order in `meaning.py`);
    `russian_source` is named for attribution.
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
    """Word card enrichment: definition, Russian, rection and muuttüüp.

    A separate request from `/api/lookup`, because it may leave the machine: a word
    card must not wait on a third party. An empty object means the lookup did not
    come back.
    """
    from .. import evs, gloss
    from ..ekidefs import lookup as native_offline
    from ..providers import sonapi
    from ..psv import lookup as psv_lookup

    words = db()
    simple = psv_lookup(words, word)
    offline_type = evs.inflection_type(words, word)
    # Always ask the live dictionary (EKI's current data) through the store: once per
    # word, within `gloss.DAILY_BUDGET`. EKI's files fill gaps and answer offline.
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
        # Found if any source had something to show.
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
