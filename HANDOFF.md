# Handoff

## Current state
PRs #72–#83 are merged. The production deep smoke passes for the current `main`
image. Cloud Run has one instance with mounted EKI audio and HARNO exam storage;
Workers AI GPT-OSS-120B is the automatic grammar/tutor lane with deterministic
fallback, and Cloudflare Workers AI is production ASR. Native A2/B1 reading
controls need private sidecars under `data/exam/`.

## Current task
Branch `claude/liquid-glass-refresh`: the glass follows iOS 27 (one
`--glass-lift` token: specular top line, foot sheen, darker outer edge), every
`role="tablist"` gets one sliding capsule (`js/glide.js`), and `html` carries
the page colour for Safari 26's toolbar tint. DESIGN.md "Adding a page or
section" and `.claude/rules/web.md` say how new screens inherit this.

## Next step
User reviews on a real iPhone/iPad in Safari and merges; after deploy run the
`smoke` workflow with `deep: true`. Uncommitted paths after commit: none.

## Open questions
Whether to let EstLLM write comprehension questions in local `cli serve`
(Estonian-only work that code verifies), and whether to raise the grammar
lane's token budget: a long sentence returned `empty reply (length)`.

## Remaining checks
Actual Chrome reminder delivery, and ASR on learner speech (Kuidas mind
kuuldakse fills as the learner reads aloud).
