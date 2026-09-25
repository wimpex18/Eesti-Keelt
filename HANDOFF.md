# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`. The calmer-surfaces visual refinement is merged.

## Current task
Open PRs, merge in this order: #72 docs refresh; #73 voice check and spoken
drill answers; #74 Reegel pages; #75 kellaaeg and kuupäevad (on #74); #76
ma-vormid (on #75); #77 pronouns, kaassõnad, käima/minema, -mine/-ja (on #76);
#78 B1 tables, kaudne kõneviis, Russian points and tips, EKK numbers (on #77).
Each passes the full suite and the browser journeys.

## Next step
User reviews and merges. Then: attested corpus clozes for sidesõnad and
määrsõnad, and the short plural partitive and superlative as drills.

## Remaining checks
Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner speech.
