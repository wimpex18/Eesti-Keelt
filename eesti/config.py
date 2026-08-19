"""Paths and tunable constants. No secrets here — those live in the environment."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
DB_PATH = Path(os.environ.get("EESTI_DB", DATA / "eesti.db"))
CONTENT_DB = Path(os.environ.get("EESTI_CONTENT_DB", DATA / "content.db"))

# The levels this tool targets. A2 matters as much as B1: the optional A2
# rehearsal sitting is 07.11.2026 (decide by 01.10.2026).
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
