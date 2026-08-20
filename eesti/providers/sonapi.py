"""Sõnaveeb lookups via api.sonapi.ee — the two fields Vabamorf cannot give.

Vabamorf generates forms; it does not know what a word *means* or what case a
verb *governs*. Two fields here fill curriculum gaps that nothing else covers:

  rection         `lugema` → "mida, kust, kellele" — this is the `rektsioon`
                  error tag, directly. Which case a verb takes is a list, not a
                  rule, and no amount of morphology derives it.
  inflectionType  the muuttüüp number (`raamat`=2, `lugema`=28) — the declension
                  type system the Notion "Nomenid A–F" page already tracks, and
                  the thing that makes a new word predictable once you know its
                  type.

Plus definitions, usage examples and translations.

**Single lookups only.** This is a third-party surface over Sõnaveeb, whose
maintainers explicitly ask people not to batch-request it. Responses are cached
on disk, and there is deliberately no bulk helper — if a caller wants a thousand
words, the answer is the Ekilex API with a key, not a loop over this.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import CACHE

BASE = "https://api.sonapi.ee/v2"

#: Short on purpose: this runs inside a request the learner is waiting on, and
#: an enrichment is never worth making a word card slow. Twenty seconds was the
#: value while nothing called this module at all.
TIMEOUT = 4.0

#: Minimum seconds between two *live* requests. Cache hits are free and are not
#: throttled.
#:
#: The module has always said "single lookups only" because Sõnaveeb's
#: maintainers ask people not to batch it. That was a comment, and a comment
#: does not stop `for word in words: lookup(word)` from running as fast as
#: Python can issue requests. This makes the promise something the code keeps:
#: a caller who loops gets throttled rather than obeyed.
MIN_INTERVAL = 1.0
_last_request = 0.0

#: `_last_request` is read, compared and written, and FastAPI runs a sync route
#: in a threadpool — so two enrichments arriving together would both read the
#: same stale stamp, both decide no wait was needed, and issue at once. The
#: throttle would then be a thing that holds only when nothing is happening,
#: which is the one time it does not matter. Serialising the read-sleep-write
#: makes the spacing hold under concurrency too.
_turn = threading.Lock()


#: The API mixes two- and three-letter codes between its two translation
#: sources. Normalised so a caller asks for one thing.
_LANG = {"rus": "ru", "eng": "en", "fra": "fr", "deu": "de", "ukr": "uk",
         "fin": "fi", "lav": "lv", "lit": "lt"}


@dataclass(frozen=True)
class WordInfo:
    word: str
    word_classes: tuple[str, ...]
    rection: str | None          # which case(s) the word governs
    inflection_type: str | None  # muuttüüp
    definition: str | None
    examples: tuple[str, ...]
    translations: dict[str, tuple[str, ...]]

    @property
    def russian(self) -> tuple[str, ...]:
        """What the word means, for the person actually using this app."""
        return self.translations.get("ru", ())

    @property
    def governs(self) -> tuple[str, ...]:
        """Rection split into individual case questions."""
        if not self.rection:
            return ()
        return tuple(p.strip() for p in self.rection.split(",") if p.strip())


def _wait_turn() -> None:
    """Hold the caller back to one live request a second."""
    global _last_request

    with _turn:
        since = time.monotonic() - _last_request
        if since < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - since)
        _last_request = time.monotonic()


def _cache_path(word: str, cache_dir: Path | None) -> Path:
    safe = urllib.parse.quote(word, safe="")
    return Path(cache_dir or CACHE) / "sonapi" / f"{safe}.json"


def fetch(word: str, cache_dir: Path | None = None) -> dict | None:
    """Raw response for one word, cached. None if the word is unknown."""
    path = _cache_path(word, cache_dir)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")) or None

    _wait_turn()
    url = f"{BASE}/{urllib.parse.quote(word)}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("null", encoding="utf-8")  # cache the miss too
            return None
        raise

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def lookup(word: str, cache_dir: Path | None = None) -> WordInfo | None:
    """The fields we actually use, or None if the word is not in Sõnaveeb."""
    payload = fetch(word, cache_dir)
    if not payload:
        return None

    results = payload.get("searchResult") or []
    if not results:
        return None
    first = results[0]

    meanings = first.get("meanings") or []
    meaning = meanings[0] if meanings else {}

    forms = first.get("wordForms") or []
    inflection_type = next(
        (f.get("inflectionType") for f in forms if f.get("inflectionType")), None
    )

    # Two translation sources come back, and the obvious one is the worse one.
    #
    # The top-level `translations` holds English only:
    #     [{"from": "et", "to": "en", "translations": ["book"]}]
    #
    # Each meaning carries its own, in three-letter codes and weighted:
    #     {"rus": [{"words": "книга", "weight": 1}, …], "eng": […], "fra": […]}
    #
    # This app is for a Russian speaker and says so in its language policy, so
    # reading only the top level threw away the field that mattered most.
    # Per-meaning first, top-level as a fallback for anything it lacks.
    translations: dict[str, tuple[str, ...]] = {}
    for code, entries in (meaning.get("translations") or {}).items():
        # Two shapes hide in one field. `words` is usually a single word, but
        # sometimes a comma-joined list of synonyms -- `lavastus` returned
        # "театральное представление,театральная постановка" as one entry. Both
        # are split, so a caller taking the first three gets three words rather
        # than one word and one paragraph.
        #
        # `dict.fromkeys` rather than a set: the list is weighted, so its order
        # is the API's own confidence ranking and a set would throw that away.
        # Repeats are real -- `hääl` came back as "голос, тон, голос".
        words = tuple(dict.fromkeys(
            part
            for e in entries
            if isinstance(e, dict) and e.get("words")
            for part in (p.strip() for p in str(e["words"]).split(","))
            if part
        ))
        if words:
            translations[_LANG.get(code, code)] = words
    for entry in payload.get("translations") or []:
        target = _LANG.get(entry.get("to") or "", entry.get("to"))
        if target and target not in translations:
            translations[target] = tuple(entry.get("translations") or ())

    return WordInfo(
        word=payload.get("estonianWord") or word,
        word_classes=tuple(first.get("wordClasses") or ()),
        rection=(meaning.get("rection") or None),
        inflection_type=str(inflection_type) if inflection_type else None,
        definition=(meaning.get("definition") or None),
        examples=tuple(meaning.get("examples") or ()),
        translations=translations,
    )


#: Sõnaveeb's own search URL. `dlall`/`dsall` are its "all dictionaries, all
#: sources" defaults — the same path the site builds when you type a word in.
SEARCH = "https://sonaveeb.ee/search/unif/dlall/dsall/{word}"


def entry_url(word: str) -> str:
    """Where to send a learner who wants more than the three fields above.

    The plan is explicit that this app does not rebuild the dictionary —
    Sõnaveeb, Sõnastik and Anki already do it better. A link honours that:
    the full paradigm, the audio and every translation are one tap away, and
    nothing here has to fetch, cache or redistribute any of it.
    """
    return SEARCH.format(word=urllib.parse.quote(word))
