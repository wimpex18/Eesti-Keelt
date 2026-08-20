"""Paths and tunable constants. No secrets here — those live in the environment."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
DB_PATH = Path(os.environ.get("EESTI_DB", DATA / "eesti.db"))
CONTENT_DB = Path(os.environ.get("EESTI_CONTENT_DB", DATA / "content.db"))

# The levels this tool targets. A2 still matters as much as B1: the 2026 A2
# rehearsal was declined (2026-08-20) in favour of another year's study, and
# the exam is now planned for 2027 — A2 then B1, or B1 alone. Which of those
# it turns out to be is exactly what the readiness verdict is for, so both
# levels stay first-class and no date is hardcoded anywhere.
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

# Research APIs are unreliable (all four GEC/analysis endpoints were 500ing
# during research). Fail fast rather than blocking the user: the observed
# TartuNLP failure mode is a 61s gateway timeout.
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
