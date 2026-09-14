"""Sõnaveeb lookups via api.sonapi.ee — what Vabamorf cannot give.

  rection         `lugema` → "mida, kust, kellele" (the `rektsioon` tag)
  inflectionType  the muuttüüp number (`raamat`=2, `lugema`=28)

Plus definitions, usage examples and translations.

**Single lookups only**: Sõnaveeb's maintainers ask not to be batch-requested.
There is no bulk helper; live requests are spaced under a lock and answers are
stored (`gloss.py`).
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

#: Short: this runs inside a request the learner is waiting on.
TIMEOUT = 4.0

#: Minimum seconds between two live requests; cache hits are not throttled, so a
#: caller that loops is slowed rather than obeyed.
MIN_INTERVAL = 1.0
_last_request = 0.0

#: Serialise the read-sleep-write of `_last_request`: sync routes run in a
#: threadpool, so concurrent enrichments would otherwise fire together.
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

    # Translations come twice: top-level `translations` is English only; each meaning
    # carries weighted `rus`/`eng`/… lists. Read per-meaning first (Russian), then the
    # top level.
    translations: dict[str, tuple[str, ...]] = {}
    for code, entries in (meaning.get("translations") or {}).items():
        # `words` may be a comma-joined list of synonyms; split it, and de-duplicate with
        # `dict.fromkeys` to keep the API's weight order.
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
    """Link to Sõnaveeb for anything beyond the stored fields: the app does not rebuild
    the dictionary.
    """
    return SEARCH.format(word=urllib.parse.quote(word))
