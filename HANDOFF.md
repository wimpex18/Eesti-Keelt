# Handoff

## Current state
PR [#67](https://github.com/wimpex18/Eesti-Keelt/pull/67) is open; the owner merges. Production is
`https://eesti-keelt.wimpex18.workers.dev`. Cloud Run has one instance
and EKI audio/HARNO exam mounts. A private off-account event export passed
`cli verify-backup` (9 events); it excludes push subscriptions and audio.

Workers AI GPT-OSS-120B is the automatic hosted grammar/tutor lane with
deterministic fallback; Cloudflare Workers AI is production ASR. Ollama EstLLM
stays outside Git and is evaluation-only. Learner ASR quality still needs
listened-to, corrected in-app recordings. Chrome reminders are subscribed;
actual delivery is unverified.

The PR adds local speech review, native PDF pages, and offline PDF extraction.
Private sidecars under `data/exam/` hold page text and OCR drafts.
Visually verified A2 and B1 reading PDFs have 6 choice and 9 figure-matching
questions; 27 other task PDFs remain ungraded. OCR text is provisional. Four milestones
derive from recorded course evidence and do not alter mastery or FSRS.

## Exact next step
After the owner merges #67, wait for Cloud Build, then run `smoke` on `main`
with `deep: true`. In Cloud Shell, pull `main`, run `cli prepare-exam` against
the existing `data/exam/`, and `deploy/push-exam.sh`; see `docs/exam-native.md`.
Verify both native tasks, HARNO pages and EKI audio on production. Check Chrome
reminder delivery and collect reviewed learner speech before paired ASR evaluation.

## Blockers
Owner merge, sidecar sync, notification arrival and verified speech are pending.
Uncommitted paths after commit: none.
