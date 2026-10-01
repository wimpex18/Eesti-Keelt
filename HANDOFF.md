# Handoff

Current task: audit source coverage, freshness and learner access.
Branch: `codex/source-refresh-audit`; PR base: `main`.
Confirmed: guests bypassed shared-corpus restoration after a cold start.
Fix: restore the owner's shared corpus before guest requests as for learners;
the forwarded request retains its guest scope and sandbox.
Regression failed before the fix and passed after it.
Verified: 2,499 Python tests passed (1 skip), 20 Worker tests, typecheck.
Production origin runs main 04930cb; the fresh deep smoke is still failing
because guest reading/exam catalogues are empty.
Next: open the focused guest-corpus PR; continue ingestion/source audit on
a separate main-based branch. Owner merges; then deploy and run deep smoke.
Uncommitted paths: none after this commit.
Blocker: reviewed fixes are not deployed until owner merge.
