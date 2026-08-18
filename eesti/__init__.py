"""Eesti-Keelt — a personal Estonian study tool for the A2/B1 tasemeeksam.

The core loop (vocabulary, morphology, drills, grading) depends on no
third-party service. Online providers are optional enrichment — see
eesti/providers/.
"""

from .env import load as _load_env

# Fill in API keys from a git-ignored .env before anything reads os.environ.
# Explicitly exported variables always win.
_load_env()

__version__ = "0.2.0"
