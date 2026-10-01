# Handoff

Current task: PM-26 deployment recovery and isolated product QA.
Branch: `codex/pm-26-worker-deployment`, stacked on PR #96.

Explicit guest headers override owner sessions and bootstrap owner access.
Speech preserves the guest sandbox through the Worker-to-origin handoff.
Smoke confirms Worker and origin guest scope before any deep submission.
Deep smoke checks generated reference audio routing, not ASR quality.
Deployment checks VPC service access before pushing secrets.
Speaking copy distinguishes Mac mini recognition from Cloudflare fallback.

Verification: 2,499 Python tests passed (1 skip); 16 Worker tests and typecheck
passed; 210 browser journeys passed (4 skips), plus 2 landscape regressions.
All 11 tabs inspected at all four required sizes in both themes.
Cloudflare deployment permission is saved and main Worker deployment succeeded.
Home health is online with the Mac mini locked; model loaded, services running,
automatic system sleep disabled. No private audio or owner-account signup used.

Next: deploy the bounded home engine label and repeat isolated deep smoke.
HTTP 422 came from a runtime fingerprint exceeding TranscriptIn's 120 chars;
two regression cases fail before and pass after the fix. PR #97 stacks on #96.
Frontend updates await owner merges and the origin build.
Uncommitted paths: none after this commit.
Blocker: live home transcription awaits deployment and generated-audio check.
The previous smoke's owner writing event remains intact; no progress was reset.
