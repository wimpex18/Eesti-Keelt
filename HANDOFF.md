# Handoff
## Current task

Pre-redesign architecture work is complete on `codex/pre-ux-architecture`.
Decision source: ADR-0005; provider evidence: `docs/ai-providers.md`;
ASR options and verified-corpus workflow: `docs/asr-evaluation.md`.

Changes cover provenance, malformed provider replies, GEC POST health,
automatic lane selection, shared tutor breakers, single interactive attempts,
thread-safe breaker persistence, verified ASR comparisons/CT2 reference,
private export replay verification and safe small-data FSRS experiments.
AGENTS.md and CLAUDE.md remain byte-identical. All changes belong to this PR.

## Exact next step

Review and merge the new architecture PR; the user merges. After deployment,
run `smoke` with `deep: true` and inspect the image build stamp.
Cloud Shell: run `deploy/check-service.sh`; verify max-instances=1,
exam/audio mounts and VAPID configuration. Their live settings were not checked.
Production smoke passed on the current main image; it does not test ASR quality.

## Remaining evidence / operations

No learner evaluation clips exist here. Record 20 pilot clips, listen/correct
transcripts, seal with `asr-verify`, then compare Workers AI and local CT2.
Do not switch production ASR without paired quality and deployment evidence.
Keep private exports outside the hosting account and run `verify-backup`.
GEC returned HTTP 500 near 60 seconds on both endpoints; NVIDIA timed out on
18/18 eval cases. Both require fresh health/quality evidence before promotion.
No unrelated uncommitted files or implementation blockers remain.
