# Handoff

## Current state
PRs #72–#84 are merged. The production deep smoke passes for the current `main`
image. Cloud Run has one instance with mounted EKI audio and HARNO exam storage;
Workers AI GPT-OSS-120B is the automatic grammar/tutor lane with deterministic
fallback, and Cloudflare Workers AI is production ASR. Native A2/B1 reading
controls need private sidecars under `data/exam/`.

## Current task
Branch `claude/project-thread-9ji581`: phone polish. The Rada pulse's Eksam
tile says `не начаты: N` on one line with a 48px flower; the Ülevaade A2/B1
switch is centred with its line; exam part rows put the contact dashes at the
row's end; an empty state's actions stack as equal capsules under 720px.

## Next step
User reviews the draft PR on a phone and merges; after deploy run the `smoke`
workflow with `deep: true`. Uncommitted paths after commit: none.

## Open questions
Whether to let EstLLM write comprehension questions in local `cli serve`
(Estonian-only work that code verifies), and whether to raise the grammar
lane's token budget: a long sentence returned `empty reply (length)`.

## Remaining checks
Actual Chrome reminder delivery, and ASR on learner speech (Kuidas mind
kuuldakse fills as the learner reads aloud).
