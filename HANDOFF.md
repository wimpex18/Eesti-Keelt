# Handoff

Current task: audit source integrations and learning-material coverage.
Branch: `codex/materials-refresh`; base: `codex/source-refresh-audit` (PR #100).

Refreshes merge by upstream URL and level, preserving issued item ids and
usable text/audio/files on partial, pointer-only and failed harvests.
Reading questions check refreshed text and never reuse old question indices.
HARNO downloads validate format before atomic replacement; --refresh rechecks
cached files. Content import validates a nonempty SQLite library before swap.
Selges pagination checks totals and rejects repeated pages.
Source catalogue checks and content/file hashes are retained as provenance.

Verified: 2,511 Python tests passed, 1 skipped; focused failure regressions pass.
222 browser journeys passed, 4 skipped; no web source files changed.
21 Worker tests and typecheck passed. Corpus restore rejection retries.
PR #100 separately fixes guest-first shared-corpus restoration; user merges.
Local private corpus: 506 items; 461 previous ids retained, 44 radio lessons
and one current news issue added; 48 HARNO files refreshed successfully.
Backup and refresh checks are in the task source-audit artifact directory.
Next: publish this focused PR, complete the
version/licensing inventory and remaining material corrections.
Uncommitted paths: none after this commit. Private corpus/exam data stays
git-ignored; learner progress is unchanged.
Blocker for production verification: owner merges the PRs before deployment.
