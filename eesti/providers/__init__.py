"""Network-backed enrichment. Every provider here is optional by design: research
inference endpoints are often down, so nothing in the core loop depends on them.
"""

from .grammar import Correction, GrammarResult, build_chain  # noqa: F401
