# ADR-0001: Grading authority

**Status:** Accepted. This file states the boundary implemented in code and
referenced by ADR-0002 and ADR-0004. Details: `docs/ai-boundaries.md`.

Drills, placement, checkpoints, grammar review and mastery use code against
issued Vabamorf/EKI or attested keys. Vocabulary review is explicitly self-rated.
Models may propose corrections, explanations, conversation turns and text-bound
reading questions, with provenance. Model scores of open production are advisory
only; they never change mastery or FSRS. Readiness reports evidence per part,
not a model-generated pass probability.

A model suggestion whose form exists in Vabamorf is still a model suggestion.
Code verification is limited to the claims it actually checks. Speech transcripts
are model output, so findings over them remain advisory regardless of which
engine checks the text. ASR comparison is not acoustic pronunciation scoring.
