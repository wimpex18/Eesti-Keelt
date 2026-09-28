# Handoff

Current task: durable acknowledgement fix and branch cleanup in PR #94.
Branch: `codex/durable-event-ack`, against `main`.

Permanent-account success confirms the response's event sequence and origin boot.
Drill/review retries preserve event identity and timing; FSRS applies a review once.
Free practice stays editable after a failed check. Worker behavior tests cover
container replacement, cursor shortcuts, failed copying and speech evidence.

Scheduled independent backups are deferred at the user's request. Backup scripts,
machine export/restore routes and secrets are removed from this PR. Private manual
exports and the existing replay verifier remain. No Mac mini backup job was installed.

Verification: 2,488 Python tests passed (1 skip); 177 browser journeys passed
(3 viewport skips); 6 Worker tests, typecheck, Wrangler dry-run and diff check passed.
Screenshots inspected across all tabs at desktop, phone, landscape and tablet sizes.
Clean checkout: Worker tests/typecheck and 43 evidence/recovery tests passed.

Next: user review/merge PR #94, then deep smoke after automated deployment.
Uncommitted paths: none after this commit. No code blockers; CI runs on push.
