# Handoff

## Current task
PR #66 is merged into `main` at `26ae1f7`. The post-merge Cloud Run image
was built at `2026-09-23T12:03:50Z`, after the merge. Deep production smoke
[35907600107](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35907600107)
passed: Access and origin guards, reference data, reading links, Ekilex, and
the live `llm:workers-ai` grammar chain. Hosted grammar/tutor stays on Workers
AI GPT-OSS-120B with deterministic fallback; Cloudflare remains production ASR.
Other grammar and ASR candidates are evaluation-only. Native TalTech controls
prove runtime feasibility, not learner accuracy.

## Exact next step
Obtain the owner's read-only Cloud Shell results from
`bash deploy/check-service.sh`, `bash deploy/push-exam.sh --check`, and
`bash deploy/push-audio.sh --check`; verify one serving instance and both
exam/audio mounts. In the installed browser/PWA, the owner opts into
`Edenemine → Meeldetuletused` and confirms an actual delivered notification.
When the owner supplies manually listened-to learner clips and transcripts
under ignored `data/eval/asr/`, seal reviews and run paired Cloudflare/TalTech
ASR evaluation. Never use displayed prompts as ground truth.
Before redesign, verify an owner's private off-account event export with
`python -m eesti.cli verify-backup /private/path/eesti-keelt-events.jsonl`.

## Blockers and working tree
`gcloud` is unavailable here; Cloud Shell access needs the owner. No learner
eval clips or private export are present in this checkout. VAPID bindings and
cron are deployed, but browser subscription/delivery is unverified. State
replication remains asynchronous. This handoff is the sole repository edit;
there are no other uncommitted files.
