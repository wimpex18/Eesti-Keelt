# Handoff

Current task: make audited source inputs and installed versions verifiable.
Branch: `codex/source-provenance`; base: `codex/materials-refresh` (PR #101).

Word-list download pins the verified upstream commit and SHA-256, validates
cached/downloaded bytes and replaces atomically. Bad TSV imports keep words
and derived forms. Docker fingerprints actual word-list and EKI input files;
health exposes those fingerprints and runtime dependency versions separately
from import row counts. HLS.js upstream licence/notices are now included.
The end-to-end source map is in docs/source-integrations.md.
Wrangler/Workers types are updated to current stable; local FastAPI matches
the production build's current stable release. No model lane was changed.

Verified: 2,514 Python tests passed, 1 skipped; 21 Worker tests, typecheck and
Worker dry-run passed. 222 browser journeys passed, 4 skipped; all 11 tabs
inspected in both themes at desktop, phone portrait/landscape and tablet.
Private local corpus has 506 items; all 461 original ids remain.
PRs #100 → #101 are ready; user merges in order. No deployment performed.
Next: publish this PR; fix truncated radio shelf
and qualify the source-backed object-case lesson; finish audit report/backlog.
Uncommitted paths: source-provenance code/Docker, dependency locks, source docs,
HLS licence, word-list tests and this handoff. Private data stays git-ignored.
Blocker for deployed changes: owner merges, then operator publishes private
corpus/exam updates and runs deep smoke.
