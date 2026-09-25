# Handoff

## Current state
PRs #72–#81 are merged. The production deep smoke passes for the current `main`
image. Cloud Run has one instance with mounted EKI audio and HARNO exam storage;
Workers AI GPT-OSS-120B is the automatic grammar/tutor lane with deterministic
fallback, and Cloudflare Workers AI is production ASR. Native A2/B1 reading
controls need private sidecars under `data/exam/`.

## Current task
Branch `claude/estllm-review` (one PR for this thread): EstLLM and GPT-OSS
measured (`docs/ai-providers.md`, `docs/evaluations/providers.json`); the
external eval scorer compares bare words; spelling advice names täpitähed only
when that is the fix; Reegel sheet, form tables, Kogu rada rows, the set head,
the drill mic and Kuidas mind kuuldakse refined to the calmer system.
NVIDIA evaluation lane pinned to DeepSeek V4.1 Flash; Qwen3.8-27B measured
as the only free Aug–Sep 2026 Workers AI model (GPT-OSS stays).

## Next step
User reviews and merges, then Cloud Build redeploys the origin; run the `smoke`
workflow with `deep: true`.

## Open questions
Whether to let EstLLM write comprehension questions in local `cli serve`
(Estonian-only work that code verifies), and whether to raise the grammar
lane's token budget: a long sentence returned `empty reply (length)`.

## Remaining checks
Actual Chrome reminder delivery, and ASR on learner speech (Kuidas mind
kuuldakse fills as the learner reads aloud).
