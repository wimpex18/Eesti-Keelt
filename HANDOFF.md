# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`. The calmer-surfaces visual refinement is merged.

## Current task
Docs refresh (branch `claude/docs-refresh`): ADR-0005 renamed to
architecture contracts, README lists every doc.

## Next step
User merges. Then: live spoken checks inside exercises, a source and endpoint
audit, and A1–B1 grammar coverage against Tere!/Keeleklikk.

## Remaining checks
Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner speech.
