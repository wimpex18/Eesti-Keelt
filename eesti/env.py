"""Load API keys from a git-ignored .env file.

Keys are read from the process environment; this only fills in values that are
not already set, so an explicitly exported variable always wins. Nothing here
ever prints a key — `describe()` reports presence and a masked tail, which is
enough to confirm the right key is loaded without putting the secret on screen
or into a log.
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import ROOT

ENV_FILE = ROOT / ".env"

# Every key the app can use. All optional: absent keys just disable that lane.
KNOWN_KEYS = {
    "OPENROUTER_API_KEY": "OpenRouter — 412 models, 15 free. The recommended one.",
    "GROQ_API_KEY": "Groq — fastest inference, generous free tier.",
    "CLOUDFLARE_API_TOKEN": "Workers AI — runs inside Cloudflare, 10k neurons/day.",
    "CLOUDFLARE_ACCOUNT_ID": "Required alongside CLOUDFLARE_API_TOKEN.",
    "ANTHROPIC_API_KEY": "Anthropic — paid, quality backstop.",
    "NOTION_TOKEN": "Notion — push confirmed errors to the Vead database.",
}


def load(path: Path | None = None, override: bool = False) -> list[str]:
    """Read KEY=value lines into the environment. Returns the names it set."""
    path = Path(path or ENV_FILE)
    if not path.exists():
        return []

    loaded = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if not value:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


def describe() -> list[tuple[str, bool, str, str]]:
    """(name, is_set, masked_value, purpose) — never the full secret."""
    out = []
    for name, purpose in KNOWN_KEYS.items():
        value = os.environ.get(name, "")
        masked = f"…{value[-4:]}" if len(value) >= 8 else ("set" if value else "—")
        out.append((name, bool(value), masked, purpose))
    return out
