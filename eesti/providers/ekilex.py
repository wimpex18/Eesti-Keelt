"""Ekilex — EKI's own dictionary API, the database Sõnaveeb shows.

## Why it replaces `api.sonapi.ee`

`sonapi` is a third party's mirror over Sõnaveeb. It has already cost this app
two defects that belong to the mirror, not to EKI: definitions joined by a bare
comma, and translations packed into one string. Ekilex is the source itself,
and EKI give it a key for exactly this use.

## What is known, and from where

Documented by EKI and confirmed in EKI-adjacent client code (2026-09-13):

* base `https://ekilex.ee/api`, key in the `ekilex-api-key` header — without it
  every call answers 403;
* `GET /word/search/{word}`, `GET /word/ids/{word}/{dataset}/est`,
  `GET /word/details/{wordId}/{dataset}`, `GET /paradigm/details/{wordId}`;
* licence CC BY 4.0: EKI and Ekilex credited, changes described.

## What the parser reads, and where it learnt it

Built from real responses (`cli ekilex-probe` for `maja`, `lugema`, `poiss`,
`kohus`, 2026-09-13; trimmed copies in `tests/fixtures/ekilex/`), not from a
description — this project has watched two parsers written that way fail on
their first real input.

`/word/details/{id}/eki` answers `word` (with `paradigms`) and `lexemes`, one
per sense, in EKI's order. From them:

* **learner definition** — a definition flagged `wwLite`: the *Keeleõppija
  Sõnaveeb* wording, the same text PSV has for `maja` but maintained today;
* **native definition** — flagged `wwUnif`;
* **Russian** — `synonymLangGroups` of `lang: rus`, **`MEANING_WORD` only**.
  `MEANING_REL` entries are words of *related* meanings, weighted below 1:
  counted, `kohus` ("duty") read угнетение, давление, иго;
* **rection** — `governments` (`lugema`: mida, kust, kellele — the object PSV lacks);
* **muuttüüp** — the first paradigm's `inflectionType`; a parenthesised one
  (`poiss`: `(22e)`) is secondary;
* **CEFR level** — `lexemeProficiencyLevelCode` (`maja` A1, `kohus` B1);
* **examples** — `usages` in Estonian.

A sense EKI mark archaic (`registers: van`, `kohus` → "право") is skipped.
Homonyms are separate word ids (`kohus`: duty, then court); the first is read,
one details request per word.

## Restraint

The same as `sonapi`, because the server is the same institute's: single
lookups only, one live request a second under a lock, no bulk helper, and every
answer kept so a word is asked about once. No rate limit is published; this is
the posture, not a workaround for one.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import CACHE
from .sonapi import WordInfo

BASE = "https://ekilex.ee/api"
HEADER = "ekilex-api-key"
KEY = "EKILEX_API_KEY"
#: EKI's combined dictionary — the dataset Sõnaveeb's main entry shows.
DATASET = "eki"

TIMEOUT = 6.0
MIN_INTERVAL = 1.0
_last_request = 0.0
_turn = threading.Lock()


def available() -> bool:
    return bool(os.environ.get(KEY, "").strip())


def _wait_turn() -> None:
    global _last_request
    with _turn:
        pause = MIN_INTERVAL - (time.monotonic() - _last_request)
        if pause > 0:
            time.sleep(pause)
        _last_request = time.monotonic()


def get(path: str, timeout: float = TIMEOUT):
    """One authenticated GET under `/api`, parsed as JSON.

    Raises `PermissionError` without a key rather than sending an
    unauthenticated request that can only answer 403.
    """
    key = os.environ.get(KEY, "").strip()
    if not key:
        raise PermissionError(f"{KEY} is not set")
    _wait_turn()
    request = urllib.request.Request(
        BASE + path, headers={HEADER: key, "Accept": "application/json",
                              "User-Agent": "Eesti-Keelt/0.1 (personal language-learning tool)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8") or "null")


def probe(word: str, out_dir: Path | None = None) -> Path:
    """Ask Ekilex about one word through every endpoint the parser will need,
    and save the raw answers side by side. Four requests, one word, once."""
    quoted = urllib.parse.quote(word)
    found: dict = {"word": word}
    found["search"] = get(f"/word/search/{quoted}")
    ids = get(f"/word/ids/{quoted}/{DATASET}/est")
    found["ids"] = ids
    if ids:
        found["details"] = get(f"/word/details/{ids[0]}/{DATASET}")
        found["paradigm"] = get(f"/paradigm/details/{ids[0]}")
    target = Path(out_dir or Path(CACHE) / "ekilex")
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{word}.json"
    path.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def shape(value, depth: int = 0, max_depth: int = 4) -> list[str]:
    """The keys of a JSON value, indented, lists summarised by their first item."""
    pad = "  " * depth
    if depth > max_depth:
        return []
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            kind = type(v).__name__
            lines.append(f"{pad}{k}: {kind}" + (f" [{len(v)}]" if isinstance(v, list) else ""))
            lines += shape(v, depth + 1, max_depth)
        return lines
    if isinstance(value, list) and value:
        return shape(value[0], depth, max_depth)
    return []


@dataclass(frozen=True)
class Info(WordInfo):
    """`sonapi.WordInfo`, plus what only Ekilex separates."""

    learner_definition: str | None = None
    level: str | None = None
    source: str = "ekilex"


ARCHAIC = "van"
MAX_RUSSIAN = 5


def _senses(details: dict) -> list[dict]:
    return [l for l in details.get("lexemes") or []
            if ARCHAIC not in {r.get("code") for r in l.get("registers") or []}]


def _definitions(lexeme: dict, flag: str) -> list[str]:
    return [d["value"] for d in (lexeme.get("meaning") or {}).get("definitions") or []
            if d.get("lang") == "est" and d.get(flag) and d.get("value")]


def _russian(lexeme: dict) -> list[str]:
    return [w["wordValue"]
            for g in lexeme.get("synonymLangGroups") or [] if g.get("lang") == "rus"
            for s in g.get("synonyms") or [] if s.get("type") == "MEANING_WORD"
            for w in s.get("words") or [] if w.get("wordValue")]


def parse(details: dict) -> Info | None:
    """One word's details, as the fields the app shows. None if nothing usable."""
    word = details.get("word") or {}
    senses = _senses(details)
    if not senses:
        return None

    # Russian: the main sense's own translations lead (poiss: мальчик,
    # мальчишка, мальчуган), then each other sense's first.
    main = list(dict.fromkeys(_russian(senses[0])))
    others = [ru[0] for ru in (_russian(l) for l in senses[1:]) if ru]
    russian = tuple(dict.fromkeys(main[:3] + others + main[3:]))[:MAX_RUSSIAN]

    learner = next((d for l in senses for d in _definitions(l, "wwLite")), None)
    native = next((d for l in senses for d in _definitions(l, "wwUnif")), None)
    rection = next((",".join(dict.fromkeys(g["value"] for g in l["governments"] if g.get("value")))
                    for l in senses if l.get("governments")), None)
    paradigm = next((p for p in word.get("paradigms") or []
                     if p.get("inflectionType") and not p["inflectionType"].startswith("(")), None)
    level = next((l["lexemeProficiencyLevelCode"] for l in senses
                  if l.get("lexemeProficiencyLevelCode")), None)
    examples = tuple(u["value"] for l in senses[:1] for u in l.get("usages") or []
                     if u.get("lang") == "est" and u.get("value"))[:3]
    pos = tuple(dict.fromkeys(p["code"] for l in senses for p in l.get("pos") or [] if p.get("code")))

    if not (russian or learner or native or rection):
        return None
    return Info(
        word=word.get("wordValue") or "",
        word_classes=pos,
        rection=rection or None,
        inflection_type=paradigm["inflectionType"] if paradigm else None,
        definition=native,
        examples=examples,
        translations={"ru": russian} if russian else {},
        learner_definition=learner,
        level=level,
    )


def lookup(word: str) -> Info | None:
    """Two requests: the word's ids, then the first id's details. None for a
    word Ekilex does not have. Raises on transport errors, like `sonapi`."""
    ids = get(f"/word/ids/{urllib.parse.quote(word)}/{DATASET}/est")
    if not ids:
        return None
    return parse(get(f"/word/details/{ids[0]}/{DATASET}") or {})
