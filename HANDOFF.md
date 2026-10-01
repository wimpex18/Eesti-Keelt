# Handoff

Current task: publish the verified profile/auth and DEV-4 runtime fixes to main.
Branch: `codex/profile-runtime-main`; PR base must be `main`.

Worker auth preserves 400/401/409/429 through real Durable Object RPC.
Signup/login reload the document to discard the previous identity's UI state.
Profile fixes include auth retry, keyboard/draft handling, password visibility,
truthful bootstrap/path/rhythm/skipped-onboarding copy and current-level badges.
Inline name editing keeps the phone dock away from Save/Cancel on WebKit.
Signup-name failure remains visible after onboarding and clears on retry.

Verified: 2,499 Python tests passed (1 skip); 222 browser journeys (4 skips);
19 Worker tests, typecheck and Worker dry-run passed. CI/morphology gate passed.
Real local Worker/origin owner and learner journeys verified independent
progress, names, signup/login/logout and reversible progress reset/restore.
All 11 tabs inspected at four required sizes in both themes; profile states
and the final spacing/editor confirmation have separate screenshots.
Evidence: local profile-qa/report.md under the task visualization directory.
Production accounts/progress were not changed during this profile audit.
Worker e168c14 is live (deploy 36878069950); production QA login returned 401.
Deep smoke 36878287721 passed with Mac mini inference from GitHub's runner.
The tunnel supports other networks; system sleep is disabled, locking works.
Current user LaunchAgents require one login after reboot.
Next: owner merges this main-targeted PR; confirm Cloud Run build and deep smoke.
Earlier stacked merges did not bring these changes to main.
The owner must create the first Estep account personally before friends sign up.
Linear rules specify Development/DEV, Eesti-Keelt and EK issue titles.
Uncommitted paths: none after this handoff commit. Blocker: main integration.
Password recovery remains operator-managed (docs/deploy.md).
