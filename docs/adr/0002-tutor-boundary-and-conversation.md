# ADR-0002: Tutor boundary and ungraded conversation

**Status:** Accepted. See ADR-0001 for grading authority.

## Decision

`eesti/tutor.py` is the boundary for model-authored corrections,
explanations, translation and conversation. The HTTP routes retain their
separate jobs and delegate model-facing work to that module. The boundary
applies provider budgets, grounding checks, provenance, and the Russian
explanation rule. Responses name the engine and distinguish model output from
deterministic evidence (`docs/ai-boundaries.md`). A model verdict never changes
mastery or FSRS.

Speech recognition stays outside this tutor boundary: it turns audio into an
advisory transcript and production inference runs in the Cloudflare Worker.
It is governed by its own quota and evaluation path (`docs/asr-evaluation.md`).

`Vestlus` plays a paired-exam partner over a speaking task. It replies in
Estonian, asks one question back, and stops at the configured turn limit. It
does not correct or score the learner. Unknown Estonian forms in the model's
reply are named rather than presented as verified language facts. The page
holds the turns during the session; evidence records only that a conversation
occurred and its size, not the transcript.

## Boundaries

- One module owns model-facing learner text, while provider transport stays in
  `eesti/providers/`.
- A failed model lane leaves available deterministic writing evidence visible.
- Routes remain separate so cached pages and route-specific error handling keep
  their contracts.
- Conversation is practice contact, never an answer key or a readiness score.
