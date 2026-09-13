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

## What is not known yet, on purpose

The response parser. This project has written two parsers against a
description of a format and watched both fail on the first real input, so this
one waits for a real response: `cli ekilex-probe WORD` saves what Ekilex answers
to `data/cache/ekilex/` (git-ignored) and prints its shape. The parser is built
from that file, and its tests from a trimmed copy of it.

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
from pathlib import Path

from ..config import CACHE

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
