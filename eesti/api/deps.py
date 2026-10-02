"""The resources a route opens, and the facts about this process.

Every database is resolved from `config` when opened, never bound at import,
so tests and callers can redirect it (`.claude/rules/python.md`).
"""

from __future__ import annotations

from contextlib import closing

import secrets
import sqlite3
from pathlib import Path

from fastapi import HTTPException
from .. import review
from ..providers import budget
from ..sources import connect as content_connect
from ..wordlist import connect

def content_db():
    """The harvested material, resolved from `config` when called."""
    from .. import config

    return content_connect(config.CONTENT_DB)


def content_available() -> bool:
    with closing(content_db()) as conn:
        return bool(conn.execute("SELECT 1 FROM items LIMIT 1").fetchone())


def content_counts() -> dict:
    with closing(content_db()) as conn:
        return {"items": conn.execute("SELECT COUNT(*) FROM items").fetchone()[0],
                "topic_links": conn.execute("SELECT COUNT(*) FROM topic_items").fetchone()[0]}


# Learner databases, resolved from `config` when opened — one source of truth for
# the app and the state snapshot.
def review_db():
    from .. import config

    return review.connect(config.learner_db("REVIEW_DB"))


def progress_db():
    from .. import config, progress

    return progress.connect(config.learner_db("PROGRESS_DB"))


def vocab_db():
    from .. import config, vocab

    return vocab.connect(config.learner_db("VOCAB_DB"))


def notion_db():
    """The queued corrections, resolved from `config` when called."""
    from .. import config
    from ..notion import connect

    return connect(config.learner_db("NOTION_DB"))


def gloss_db():
    """Word meanings, in `vocab.db` so the state snapshot carries them (see
    `eesti/gloss.py`).
    """
    from .. import config, gloss

    return gloss.connect(config.learner_db("VOCAB_DB"))


# Generated items are not stored: the client returns the item with the answer and
# the server re-grades it. Signed item refs bind the answer to the issued prompt
# across guest sandboxes and permanent accounts.

#: The page and its static files. `parents[1]`, not `parent`: this module
#: lives in `eesti/api/` and the web directory is `eesti/web/`.
WEB = Path(__file__).resolve().parents[1] / "web"


# Identifies this process. The Worker reads it from every response; a new id means
# a fresh container with an empty disk, so the snapshot is pushed back in.
BOOT_ID = secrets.token_hex(8)


PROXY_HEADER = "x-proxy-token"


def db():
    return connect()


def owner_scope() -> None:
    """FastAPI dependency for routes that act on the owner's private data."""
    from ..identity import OWNER, current

    if current().kind != OWNER:
        raise HTTPException(status_code=403,
                            detail="Эта операция доступна только владельцу приложения.")


def allowance_db() -> sqlite3.Connection:
    """Open the allowance store for the current request scope.

    Permanent accounts share the owner's snapshotted store. Guest sandboxes
    share a smaller, ephemeral store that is never copied to a Durable Object.
    """
    from .. import config
    from ..identity import current

    path = config.guest_shared_db() if current().is_guest else config.PROGRESS_DB
    return sqlite3.connect(path)


def _bind_breaker() -> None:
    """Point the provider breaker at the learner's database.

    Persisting in `progress.db` means it survives Cloud Run cold starts via the
    snapshot. An opener is registered, so no path is resolved until the breaker
    first has something to record.
    """
    from ..providers import breaker

    breaker.bind_later(progress_db)
    budget.bind_later(allowance_db)


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
