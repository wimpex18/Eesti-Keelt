# Handoff

## Current state
PRs #72–#84 are merged. The production deep smoke passes for the current `main`
image. Cloud Run has one instance with mounted EKI audio and HARNO exam storage;
Workers AI GPT-OSS-120B is the automatic grammar/tutor lane with deterministic
fallback, and Cloudflare Workers AI is production ASR. Native A2/B1 reading
controls need private sidecars under `data/exam/`.

## Current task
Branch `claude/evs-examples`: the word card's *Näited* shows EKI EVS's example
phrases with their Russian (137 316 for 34 802 lemmas, `evs_example`, imported
by `cli import-evs`), three shown and the rest folded, credited to EKI.

## Next step
User reviews the PR and merges; Cloud Build re-imports EVS in the image. After
deploy run the `smoke` workflow with `deep: true`. Uncommitted paths: none.

## Open questions
Whether to let EstLLM write comprehension questions in local `cli serve`
(Estonian-only work that code verifies), and whether to raise the grammar
lane's token budget: a long sentence returned `empty reply (length)`.

## Remaining checks
Actual Chrome reminder delivery, and ASR on learner speech (Kuidas mind
kuuldakse fills as the learner reads aloud).
