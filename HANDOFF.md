# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`.

## Current task
Review and merge the "Laudtee" interface redesign PR (`DESIGN.md`): a new
visual system (cornflower/black/birch, self-hosted Onest + Literata), a spine
and rail layout, a phone thumb dock, the Rada hero with its boardwalk, answer
beads, the readiness cornflower, milestone seals and a rebuilt progress report.
Backend additions only: `contact`/`contact_target` on readiness parts, `ru` on
curriculum topics, `/fonts/{name}`, and raw rule ids no longer shown in the
plan. Two practice-set bugs are fixed: the end card listed right answers as
misses, and `Selgita` was wiped by the verdict it belonged to.

## Next step
After merge, run `smoke` with `deep: true` and look at the deployed app on the
phone (installed PWA) and desktop. Uncommitted paths after commit: none.

## Remaining checks
Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner recordings reviewed inside `Hindamiskomplekt`.
