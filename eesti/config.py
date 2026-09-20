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

# Provider timeout: research APIs often hang (TartuNLP's failure mode is a ~60 s
# gateway timeout), so fail fast and fall through.
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

# EKI's spoken word forms and read sentences (`eesti/haaldus.py`): imported, not
# built, and 270 MB, so it neither ships in the image nor travels in a snapshot.
# On the deployment it is a Cloud Storage bucket mounted read-only into the
# container (`deploy/push-audio.sh`), which is why the path is an environment
# variable rather than a constant.
AUDIO_DB = os.environ.get("EESTI_AUDIO_DB", "data/audio.db")
