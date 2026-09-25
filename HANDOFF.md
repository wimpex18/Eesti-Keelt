# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`.

## Current task
Stack #72–#80 with the code-review fixes applied in the PR that introduced each
one, and each branch merged into the next. #74 contains #73 (their path.js and
app.css edits overlapped), so merge #73 before #74.

## Next step
User merges #72, #73, then #74–#79 in order, then #80.
Uncommitted paths after commit: none.

## Remaining checks
Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner recordings reviewed inside `Hindamiskomplekt`.
