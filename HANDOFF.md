# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`. The calmer-surfaces visual refinement is merged.

## Current task
Open PRs, merge in this order: #72 docs refresh; #73 voice check and spoken
drill answers; #74 Reegel pages (contains #73: their path.js and app.css edits
overlapped); #75 kellaaeg and kuupäevad (on #74); #76 ma-vormid (on #75); #77
pronouns, kaassõnad, käima/minema, -mine/-ja (on #76); #78 B1 tables, kaudne
kõneviis, Russian points and tips, EKK numbers (on #77); #79 mul on / mulle
meeldib (on #78); #80 sidesõnad, määrsõnad, parallel case forms, native reading
smoke, journeys in CI (on #79, contains #72). Code-review fixes sit in the PR
that introduced each defect and are merged down the stack.

## Next step
User merges in the order above. After merge, watch the new `journeys` CI job.
Uncommitted paths after commit: none.

## Remaining checks
Actual Chrome reminder delivery, and ASR on learner speech (Kuidas mind
kuuldakse fills as the learner reads aloud).
