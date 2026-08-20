"""Load API keys from a git-ignored .env file.

Keys are read from the process environment; this only fills in values that are
not already set, so an explicitly exported variable always wins. Nothing here
ever prints a key — `describe()` reports presence and a masked tail, which is
enough to confirm the right key is loaded without putting the secret on screen
or into a log.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .config import ROOT

ENV_FILE = ROOT / ".env"

# Every key the app can use. All optional: absent keys just disable that lane.
KNOWN_KEYS = {
    "OPENROUTER_API_KEY": "OpenRouter — 412 models, 15 free. The recommended one.",
    "GROQ_API_KEY": "Groq — fastest inference, generous free tier.",
    "CLOUDFLARE_API_TOKEN": "Workers AI — runs inside Cloudflare, 10k neurons/day.",
    "CLOUDFLARE_ACCOUNT_ID": "Required alongside CLOUDFLARE_API_TOKEN.",
    "HF_TOKEN": "Hugging Face — the only hosted route to EstLLM (Estonian-adapted).",
    "ANTHROPIC_API_KEY": "Anthropic — paid, quality backstop.",
    "NOTION_TOKEN": "Notion — push confirmed errors to the Vead database.",
}


#: A POSIX environment-variable name. Anything else cannot be read back by
#: `os.environ.get(...)`, so setting it is worse than skipping it.
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load(path: Path | None = None, override: bool = False) -> list[str]:
    """Read KEY=value lines into the environment. Returns the names it set.

    Only names it actually set. That distinction is the point: a line reading
    `export OPENROUTER_API_KEY=sk-...` -- which is what you get from copying
    any shell instruction -- used to set a variable literally called
    `"export OPENROUTER_API_KEY"`, report it as loaded, and leave the real key
    unset. The grammar chain then ran in offline mode with the key apparently
    configured, which is a confusion this project has already paid for once.

    So `export ` is stripped, and a name that is not a legal environment
    variable is skipped rather than set and announced.
    """
    path = Path(path or ENV_FILE)
    if not path.exists():
        return []

    loaded = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip().strip('"').strip("'")
        if not value or not _NAME.match(key):
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
