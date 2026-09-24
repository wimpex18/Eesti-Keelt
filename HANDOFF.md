# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`.

## Current task
Review and merge PR #69, the "Laudtee" interface (`DESIGN.md`): Estonian blue
on near-white, Geologica and Phosphor self-hosted, glass navigation, the gate,
boardwalk, readiness flower, practice rhythm and review forecast. Backend
additions are read-only projections: `contact`/`contact_target` on readiness,
`ru`/`gate`/`resume_recent` on `/api/curriculum`, `rhythm` on `/api/status`,
`forecast` on `/api/review/stats`, and `/fonts/{name}`.

## Next step
After merge, run `smoke` with `deep: true`, install the PWA again on the phone
(the icon changed) and look at it in both themes. Uncommitted paths after
commit: none.

## Remaining checks
Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner recordings reviewed inside `Hindamiskomplekt`.
