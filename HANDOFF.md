# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`.

## Current task
Review and merge the Laudtee polish PR (#70): fixed desktop sidebar, pulse tiles,
folding dock, closable word card, plural fixes; plus the Mängija audio player
over every `<audio>`, Sõnatrenn (word workout from the learner's `õpin` words),
a one-line reader source, exam text/native routes answering `available: false`
instead of 404, a fast learner-status filter in `vocab.browse`, and wrangler /
workers-types upgrades.

## Next step
After merge, run `smoke` with `deep: true` and look at the phone PWA in both
themes. Uncommitted paths after commit: none.

## Remaining checks
Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner recordings reviewed inside `Hindamiskomplekt`.
