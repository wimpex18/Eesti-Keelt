"""The resources a route opens, and the facts about this process.

Split out of `app.py` so that a router imports what it needs rather than the
whole application. Every database here is resolved from `config` **when it is
opened**, never from a copy bound at import: a path frozen at import cannot be
pointed anywhere else, which is the bug this project has paid for often enough
to have a rule about it (`docs/lessons.md`, *Paths, connections and state*).
"""

from __future__ import annotations

import secrets
from pathlib import Path

from .. import review
from ..sources import connect as content_connect
from ..wordlist import connect

def content_db():
    """The harvested material, resolved when called.

    A module-level `CONTENT_DB = "data/content.db"` sat here and bypassed
    `config.CONTENT_DB` entirely, so redirecting the database had no effect on
    the web app — which is how a read-aloud endpoint passed locally and returned
    an empty list in CI. Same shape as the bug in `wordlist.connect`: a path
    frozen at import cannot be pointed anywhere else.
    """
    from .. import config

    return content_connect(config.CONTENT_DB)


def content_available() -> bool:
    from .. import config
    from ..sources import available

    return available(config.CONTENT_DB)


# Every learner database is resolved from `config` when opened, never from a
# copy bound here at import. `app.py` used to hold its own module globals for
# these four, so redirecting them meant patching two modules that could drift
# apart -- and they did: `_state_paths()` read one set and these helpers the
# other, so a snapshot could restore into a different file from the one the
# app then read. One source, read at call time.
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
    """The queued corrections, resolved when called.

    This was the last path in the app read from a module global bound at
    import — the notion routes closed over `app.NOTION_DB` while every other
    database went through `config`, which is the two-homes-for-one-value shape
    `docs/lessons.md` warns about. One source, read at call time.
    """
    from .. import config
    from ..notion import connect

    return connect(config.NOTION_DB)


def gloss_db():
    """Word meanings, in `vocab.db` so the state snapshot carries them.

    Anywhere else and the store would evaporate on every Cloud Run cold start,
    which is the bug it exists to fix — see `eesti/gloss.py`.
    """
    from .. import config, gloss

    return gloss.connect(config.VOCAB_DB)


# Generated items are not stored, so an answer arrives without the question. The
# client sends the item back with the answer and the server re-grades it, which
# keeps the API stateless — but it also means the client could send an item it
# was never given. That is fine for a single-user app behind Cloudflare Access
# and would not be for a multi-user one: the fix there is to sign the item or
# hold the session server-side, and this note exists so that is a decision
# rather than an oversight.

#: The page and its static files. `parents[1]`, not `parent`: this module
#: lives in `eesti/api/` and the web directory is `eesti/web/`.
WEB = Path(__file__).resolve().parents[1] / "web"


# Identifies this process. The Worker in front of the deployment reads it off
# every response: when it changes, the container it was talking to has been
# replaced and its disk is empty again, which is the cue to push the snapshot
# back in. Cloud Run scales to zero and gives no shutdown hook the Worker can
# see, so the boot id is how a restart is noticed at all.
BOOT_ID = secrets.token_hex(8)


PROXY_HEADER = "x-proxy-token"


def db():
    return connect()


def _bind_breaker() -> None:
    """Point the provider breaker at the learner's database.

    Without this the breaker is per-process, and on Cloud Run — which scales to
    zero — that meant every cold container paid a dead provider's full timeout
    twice before stepping over it. `progress.db` rather than a file of its own
    so it rides the existing snapshot; the table is tiny and its lifetime is
    the same as the deployment's.

    Registered rather than opened. This used to call `progress_db()` here, at
    module scope, which resolved the database path at *import* — the exact
    anti-pattern this project has a written habit about, and the reason the
    test suite had to re-bind after the fact to stop the breaker reaching for
    the learner's real file. The breaker now opens it the first time it has
    something to remember, by which point any caller has had its chance to
    point the path somewhere else.
    """
    from ..providers import breaker

    breaker.bind_later(progress_db)


# Called here, at import, and that placement is the whole point: the breaker
# has to be pointed at the learner's database before anything asks it whether a
# provider is dead. Registering an *opener* is what makes that safe -- no path
# is resolved until the breaker first has something to remember.
#
# It was lost for one commit in the split that made this module: the call is a
# bare expression with no name, and the tool that carved `app.py` up moved
# functions, classes and assignments. Nothing failed. The breaker fell back to
# a module-level dict, which on Cloud Run means every cold container pays a
# dead provider's full timeout twice -- the exact thing the durable store
# exists to prevent, and invisible to the suite because `conftest` unbinds it
# deliberately.
_bind_breaker()


def build_info() -> dict:
    """When this image was built, and from what commit if the builder said.

    Read once and cached by the module-level call below: it is a file written
    at image build time and it cannot change while the process runs.

    Why it exists: a Python change was merged, the Worker redeployed, and the
    new endpoint was still absent from production — with no way to tell whether
    the container build had not run yet, had failed, or was never wired up.
    Running from a source checkout there is no file and no build, which is
    itself the honest answer.
    """
    import json
    from pathlib import Path

    try:
        return json.loads((Path("/app") / "BUILD_INFO").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"built": None, "revision": None}


BUILD = build_info()
