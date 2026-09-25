# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`.

## Current task
Visual refinement PR (branch `claude/calmer-surfaces`): flat primary buttons,
neutral secondary/icon controls, hairline depth instead of shadows, no page
glows, fewer type sizes/weights, Sõnatrenn as an on-page practice space.

## Next step
User reviews screenshots and merges. Uncommitted paths after commit: none.

## Remaining checks
Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner recordings reviewed inside `Hindamiskomplekt`.
