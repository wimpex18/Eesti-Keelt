# Handoff

Current task: DEV-4 deployment recovery and isolated product QA.
Branch: `codex/pm-26-worker-deployment`, stacked on PR #96.

Explicit guest headers override owner sessions and bootstrap owner access.
Speech preserves the guest sandbox through the Worker-to-origin handoff.
Smoke confirms Worker and origin guest scope before any deep submission.
Deployment checks VPC service access before pushing secrets.
Speaking copy distinguishes Mac mini recognition from Cloudflare fallback.

Verification: 2,499 Python tests passed (1 skip); 16 Worker tests and typecheck
passed; 210 browser journeys passed (4 skips), plus 2 landscape regressions.
All 11 tabs inspected at all four required sizes in both themes.
Cloudflare deployment permission is saved and main Worker deployment succeeded.
Production deep smoke 36867253978 passed from an external GitHub runner:
Mac mini transcribed generated audio with its screen locked/dark; grammar used
Workers AI. Deployment 36843614692 succeeded; PR #96/#97 CI is green.
Automatic system sleep was already disabled. Login once after reboot is needed
for the user LaunchAgents; screen lock/display sleep keeps them running.

Next: owner reviews/merges #96, then #97. DEV-4 is In Review.
Bounded home engine labels prevent HTTP 422; full fingerprints remain in
the home service/eval. Both regressions fail before and pass after the fix.
AGENTS.md changes only the existing Linear section: Development/DEV,
Eesti-Keelt project, new titles start EK. Existing tracking rules unchanged.
Frontend updates await owner merges and the origin build.
Uncommitted paths: none after this commit.
Blockers: none for the confirmed fixes; private learner-ASR quality untested.
The previous smoke's owner writing event remains intact; no progress was reset.
