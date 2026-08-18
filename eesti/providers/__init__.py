"""Network-backed enrichment. Every provider here is optional by design.

During research, four separate research-hosted inference endpoints (TartuNLP
grammar /v1 and /v2, ELLE's CEFR predictor and corrector) were all returning
HTTP 500, while every dataset and static asset worked fine. That is the normal
state of grant-funded infrastructure, not an outage — so nothing in the core
loop may depend on these.
"""

from .grammar import Correction, GrammarResult, build_chain  # noqa: F401
