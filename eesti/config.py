"""Paths and tunable constants. No secrets here — those live in the environment."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
DB_PATH = Path(os.environ.get("EESTI_DB", DATA / "eesti.db"))
CONTENT_DB = Path(os.environ.get("EESTI_CONTENT_DB", DATA / "content.db"))

# The levels this tool targets. The exam is planned for 2027 — A2 then B1, or
# B1 alone — so both stay first-class and no date is hardcoded.
LEVELS = ("A1", "A2", "B1")

# Error tags — these MUST stay identical to the fixed multi_select options in
# the Notion "Vead" database, or pushed rows will not group with existing ones.
TAGS = (
    "obj-case",
    "loc-case",
    "gen-stem",
    "gradation",
    "verb-form",
    "ma-da-inf",
    "word-order",
    "vocab",
    "rektsioon",
)

# Interactive fallback budget, not a claim about service completion latency.
# Public GEC splits this socket timeout equally between its two endpoints.
PROVIDER_TIMEOUT = 5.0

TARTUNLP_GRAMMAR = "https://api.tartunlp.ai/grammar/v2"
TARTUNLP_TTS = "https://api.tartunlp.ai/text-to-speech/v2"
TARTUNLP_TRANSLATE = "https://api.tartunlp.ai/translation/v2"


# Learner databases. Here rather than in `app.py` because the CLI needs them
# too, and importing the web application to learn a file path drags FastAPI and
# every provider into a terminal command that wanted one string.
REVIEW_DB = "data/review.db"
PROGRESS_DB = "data/progress.db"
VOCAB_DB = "data/vocab.db"
NOTION_DB = "data/notion.db"
# The evidence log (`eesti/evidence.py`): the source the four above are rebuilt from.
EVENTS_DB = "data/events.db"

# Other permanent learners (ADR-0006): one directory per learner id, each with
# its own five learner files, restored by that learner's Durable Object. The
# owner keeps the paths above.
LEARNERS_DIR = os.environ.get("EESTI_LEARNERS_DIR", "data/learners")

# Guest sandboxes (ADR-0006): one directory per sandbox. Their allowance is
# counted in the owner's `progress.db` (`providers/budget.py`). On Cloud Run
# this is ephemeral disk, never snapshotted.
GUEST_DIR = os.environ.get("EESTI_GUEST_DIR", "data/guest")

_LEARNER_FILES = {
    "PROGRESS_DB": "progress.db",
    "REVIEW_DB": "review.db",
    "VOCAB_DB": "vocab.db",
    "NOTION_DB": "notion.db",
    "EVENTS_DB": "events.db",
}


def learner_db(name: str) -> str:
    """The learner database `name` ("PROGRESS_DB", ...) for the current request.

    The owner's path is this module's own attribute, read at call time, so a
    test that redirects `config.PROGRESS_DB` still redirects the owner. Another
    learner, or a guest, gets the same file name inside its own directory.
    """
    from .identity import GUEST, OWNER, current

    scope = current()
    if scope.kind == OWNER:
        return globals()[name]
    root = GUEST_DIR if scope.kind == GUEST else LEARNERS_DIR
    target = Path(root) / scope.id / _LEARNER_FILES[name]
    target.parent.mkdir(parents=True, exist_ok=True)
    return str(target)


# The exam board's own task files (`eesti/harvest/harno.py`): PDFs and listening
# audio, downloaded for study and never committed.
EXAM_DIR = os.environ.get("EESTI_EXAM_DIR", "data/exam")

# EKI's spoken word forms and read sentences (`eesti/haaldus.py`): imported, not
# built, and 270 MB, so it neither ships in the image nor travels in a snapshot.
# On the deployment it is a Cloud Storage bucket mounted read-only into the
# container (`deploy/push-audio.sh`), which is why the path is an environment
# variable rather than a constant.
AUDIO_DB = os.environ.get("EESTI_AUDIO_DB", "data/audio.db")
