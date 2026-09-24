# Handoff

## Current state
The production deep smoke passes for the current `main` image. Cloud Run has one
instance with mounted EKI audio and HARNO exam storage; Workers AI GPT-OSS-120B
is the automatic grammar/tutor lane with deterministic fallback, and Cloudflare
Workers AI is production ASR. Native A2/B1 reading controls need private
sidecars under `data/exam/`.

## Current task
Review and merge the Laudtee polish PR: the fixed desktop sidebar, the pulse
tiles on phone and iPad Rada, the dock that folds while scrolling, a closable
word card, mock and exam-shape sizing, Russian plural and wording fixes, and
`.claude/launch.json` kept out of the repository. No backend contract changes.

## Next step
After merge, run `smoke` with `deep: true` and look at the phone PWA in both
themes. Uncommitted paths after commit: none.

## Remaining checks
Verify the two native reading controls in production, actual Chrome reminder
delivery, and ASR on learner recordings reviewed inside `Hindamiskomplekt`.
