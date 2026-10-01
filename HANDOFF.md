# Handoff

Current task: profile/account QA and confirmed fixes.
Branch: `codex/profile-account-qa`, stacked on PR #97 (which follows #96).

Worker auth preserves 400/401/409/429 through real Durable Object RPC.
Signup/login reload the document to discard the previous identity's UI state.
Profile fixes include auth retry, keyboard/draft handling, password visibility,
truthful bootstrap/path/rhythm/skipped-onboarding copy and current-level badges.
Inline name editing keeps the phone dock away from Save/Cancel on WebKit.
Signup-name failure remains visible after onboarding and clears on retry.

Verified: 2,499 Python tests passed (1 skip); 222 browser journeys (4 skips);
19 Worker tests, typecheck and Worker dry-run passed.
Real local Worker/origin owner and learner journeys verified independent
progress, names, signup/login/logout and reversible progress reset/restore.
All 11 tabs inspected at four required sizes in both themes; profile states
and the final spacing/editor confirmation have separate screenshots.
Evidence: local profile-qa/report.md under the task visualization directory.
Production accounts/progress were not changed during this profile audit.

Next: push/open stacked PR against #97, deploy the Worker auth fix,
verify its production error and run the deep smoke workflow.
Frontend changes await owner merges #96, #97, then this profile PR.
The owner must create the first Estep account personally before friends sign up.
Uncommitted paths: HANDOFF.md, DESIGN.md, docs/identity.md, deploy/accounts.ts,
deploy/worker.ts, eesti/web/app.css, eesti/web/js/profile.js,
eesti/web/js/onboarding.js, package.json, tests/test_e2e_journeys.py,
tests/worker-auth.test.mjs; all are included in the prepared change.
Blockers: none for the confirmed fixes; self-service password reset is absent.
