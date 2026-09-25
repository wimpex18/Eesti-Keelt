# Handoff

## Current state
PRs #72–#81 are merged. The production deep smoke passes for the current `main`
image. Cloud Run has one instance with mounted EKI audio and HARNO exam storage;
Workers AI GPT-OSS-120B is the automatic grammar/tutor lane with deterministic
fallback, and Cloudflare Workers AI is production ASR. Native A2/B1 reading
controls need private sidecars under `data/exam/`.

## Current task
Branch `claude/calmer-surfaces`: the external eval classes each fix by its
original (capitalised) words, so a proper-noun case fix is no longer counted
as spelling. An iPhone-sized pass found and fixed a first-open race in
`gloss.migrate` (500 on `/api/status`) and a stale question under Rääkimine's
sentence mode when no sentences load.

## Next step
User reviews and merges; after deploy run the `smoke` workflow with
`deep: true`. Uncommitted paths after commit: none.

## Open questions
Whether to let EstLLM write comprehension questions in local `cli serve`
(Estonian-only work that code verifies), and whether to raise the grammar
lane's token budget: a long sentence returned `empty reply (length)`.

## Remaining checks
Actual Chrome reminder delivery, and ASR on learner speech (Kuidas mind
kuuldakse fills as the learner reads aloud).
