# Handoff

## Current state
PR [#67](https://github.com/wimpex18/Eesti-Keelt/pull/67) is open on
`codex/post-merge-ops-handoff`; the owner merges. Production is
`https://eesti-keelt.wimpex18.workers.dev`. Cloud Run revision
`eesti-keelt-00077-n7t` has one maximum instance and EKI audio/HARNO exam mounts; deep smoke must run on `main` after the merge and Cloud Build deploy.

Workers AI GPT-OSS-120B is automatic hosted grammar/tutor with deterministic
fallback; Cloudflare Workers AI is production ASR. Ollama EstLLM lives outside
Git at `~/.ollama/models` and remains evaluation-only. The audited grammar
trial caught 9/10 planted errors but left 0/8 clean controls alone; see
`docs/evaluations/hand-set.md` for the labels and EKI checks.

`Vestlus` supports mic → editable ASR text → tutor reply → TTS. Local-only
`Hindamiskomplekt` saves selected clips with a listened-to, verified transcript;
ordinary practice audio is unsaved. Official PDF pages, raw text and audio
display in-app; structured tasks and figures are not imported. Controls align.
Chrome reminders are subscribed; delivery is unverified. A private off-account
event export passed `cli verify-backup` (9 events); it excludes push
subscriptions and audio.

## Exact next step
After the owner merges #67 and Cloud Build deploys, run GitHub `smoke` on
`main` with `deep: true`; verify a HARNO PDF page and EKI audio through the
mounts. Check Chrome reminder delivery at an eligible hour. Collect learner
speech in-app, listen and correct transcripts, then run paired ASR evaluation.

## Blockers
Owner merge, notification arrival and human-verified speech are pending.
