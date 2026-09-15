"""The resources a route opens, and the facts about this process.

Every database is resolved from `config` when opened, never bound at import,
so tests and callers can redirect it (`.claude/rules/python.md`).
"""

from __future__ import annotations

import secrets
from pathlib import Path

from .. import review
from ..sources import connect as content_connect
from ..wordlist import connect

def content_db():
    """The harvested material, resolved from `config` when called."""
    from .. import config

    return content_connect(config.CONTENT_DB)


def content_available() -> bool:
    from .. import config
    from ..sources import available

    return available(config.CONTENT_DB)


def content_counts() -> dict:
    from .. import config
    from ..sources import corpus_counts

    return corpus_counts(config.CONTENT_DB)


# Learner databases, resolved from `config` when opened — one source of truth for
# the app and the state snapshot.
def review_db():
    from .. import config

    return review.connect(config.REVIEW_DB)


def progress_db():
    from .. import config, progress

    return progress.connect(config.PROGRESS_DB)


def vocab_db():
    from .. import config, vocab

    return vocab.connect(config.VOCAB_DB)


def notion_db():
    """The queued corrections, resolved from `config` when called."""
    from .. import config
    from ..notion import connect

    return connect(config.NOTION_DB)


def gloss_db():
    """Word meanings, in `vocab.db` so the state snapshot carries them (see
    `eesti/gloss.py`).
    """
    from .. import config, gloss

    return gloss.connect(config.VOCAB_DB)


# Generated items are not stored: the client returns the item with the answer and
# the server re-grades it. Fine for one learner behind Access; a multi-user app
# would need signed items or server-side sessions.

#: The page and its static files. `parents[1]`, not `parent`: this module
#: lives in `eesti/api/` and the web directory is `eesti/web/`.
WEB = Path(__file__).resolve().parents[1] / "web"


# Identifies this process. The Worker reads it from every response; a new id means
# a fresh container with an empty disk, so the snapshot is pushed back in.
BOOT_ID = secrets.token_hex(8)


PROXY_HEADER = "x-proxy-token"


def db():
    return connect()


def _bind_breaker() -> None:
    """Point the provider breaker at the learner's database.

    Persisting in `progress.db` means it survives Cloud Run cold starts via the
    snapshot. An opener is registered, so no path is resolved until the breaker
    first has something to record.
    """
    from ..providers import breaker

    breaker.bind_later(progress_db)


# Must run at import, before any provider is asked whether it is dead;
# registering an opener keeps that safe. (`conftest` unbinds it in tests.)
_bind_breaker()


def build_info() -> dict:
    """When this image was built, and from what commit if the builder said.

    Read once from `/app/BUILD_INFO`; a source checkout has none, which is itself
    the answer.
    """
    import json
    from pathlib import Path

    try:
        return json.loads((Path("/app") / "BUILD_INFO").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"built": None, "revision": None}


BUILD = build_info()
