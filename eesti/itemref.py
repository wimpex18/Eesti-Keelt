"""Signed item references: the server's own record of an item it handed out.

A generated item is not stored: it is regenerated. Its *ref* says how: the
generator's inputs (topic, seed, count, levels, theme, rules) and the item's
place in the set. `regenerate(ref)` gives the same item back, which is what lets
an attempt in the evidence log be replayed.

The page receives each item with a *token*: the ref and the item's gradable
fields, HMAC-signed. The answer comes back with the token, so the server grades
against what it issued, not against an answer key the page sends back. A
tampered token is refused.

The key comes from `ITEM_SECRET`, else `PROXY_TOKEN` or `STATE_TOKEN` (both
secrets the deployment already has), else a fixed development key under
`cli serve`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

#: Bumped when a generator's output for the same inputs changes, so an old ref
#: is known not to regenerate the item it named.
GENERATOR_VERSION = 1

#: Item fields the answer endpoint grades and records from.
FIELDS = ("topic", "prompt", "answer", "distractor", "lemma", "hint", "rule", "why_ru")


def _key() -> bytes:
    secret = (os.environ.get("ITEM_SECRET") or os.environ.get("PROXY_TOKEN")
              or os.environ.get("STATE_TOKEN") or "eesti-keelt-local-development")
    return hashlib.sha256(b"eesti-item:" + secret.encode()).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(item, ref: dict) -> str:
    """A token for one issued item."""
    fields = {name: getattr(item, name, "") or "" for name in FIELDS}
    body = json.dumps({"ref": ref, "item": fields}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":")).encode()
    mac = hmac.new(_key(), body, hashlib.sha256).hexdigest()[:32]
    return f"{_b64(body)}.{mac}"


def verify(token: str) -> dict:
    """`{"ref": ..., "item": ...}` from a token, or ValueError if it was not ours."""
    try:
        body_b64, mac = token.rsplit(".", 1)
        body = _unb64(body_b64)
    except (ValueError, TypeError) as exc:
        raise ValueError("malformed item token") from exc
    expected = hmac.new(_key(), body, hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(mac, expected):
        raise ValueError("item token signature does not match")
    return json.loads(body)


def practice_ref(topic: str, *, seed: int, count: int, levels, theme, rules,
                 index: int) -> dict:
    return {"kind": "practice", "v": GENERATOR_VERSION, "topic": topic,
            "seed": seed, "count": count, "levels": list(levels),
            "theme": theme, "rules": list(rules) if rules else None, "index": index}


def checkpoint_ref(level: str, *, seed: int, count: int, index: int) -> dict:
    return {"kind": "checkpoint", "v": GENERATOR_VERSION, "level": level,
            "seed": seed, "count": count, "index": index}


def regenerate(ref: dict):
    """The item a ref names, generated again from the same inputs."""
    if ref.get("v") != GENERATOR_VERSION:
        raise ValueError(f"ref from generator version {ref.get('v')}, now {GENERATOR_VERSION}")
    if ref["kind"] == "practice":
        from .practice import items_for

        items = items_for(ref["topic"], count=ref["count"], levels=tuple(ref["levels"]),
                          seed=ref["seed"], theme=ref["theme"],
                          rules=tuple(ref["rules"]) if ref["rules"] else None)
    elif ref["kind"] == "checkpoint":
        from .checkpoint import build

        items = build(ref["level"], count=ref["count"], seed=ref["seed"])
    else:
        raise ValueError(f"unknown ref kind {ref['kind']!r}")
    return items[ref["index"]]
