# Handoff

## Current task
Provider/source follow-up is complete on `codex/pre-ux-architecture`, PR #66.
Automatic hosted grammar/tutor: Workers AI GPT-OSS-120B only, then deterministic
fallback. Public GEC, normalization, Mistral/NVIDIA/OpenRouter remain eval-only.
Modern candidates and exact results: `docs/evaluations/providers.json`.
TTS/translation and EKI/ERR/Selges/HARNO/EIS passed independent runtime probes.
Source refresh/publication, TTS cache validation and translation parsing fixed.
TalTech CT2/Zipformer actually ran native controls; no learner quality claim.
ASR reference decoding/fingerprints and open-answer question-context eval fixed.
All changes belong to this PR; AGENTS.md and CLAUDE.md remain byte-identical.

## Exact next step
Review/merge PR #66 (the user merges), then run `smoke` with `deep: true` and
verify the image stamp. Branch application changes are not deployed yet.
VAPID pair is in ignored .env + GitHub secrets; main Worker deploy succeeded
and all three live VAPID bindings/hourly cron were verified. No push was sent.

## Remaining owner actions / limits
Opt into reminders in the installed browser/PWA and verify actual delivery.
Record/verify learner ASR clips; native controls do not measure false acceptance.
Use `asr-verify --question` only for the real open-answer question, never a target.
Cloud Shell: check max-instances=1 and exam/audio mounts; gcloud access unavailable here.
Take a private off-account export and run `verify-backup` before redesign.
Replication is asynchronous; coordinated erasure/nightly backups remain deferred.
Latest full local suite: 2208 passed, 2 skipped; morphology gold check 98.1%.
No unrelated uncommitted files or implementation blockers remain.
