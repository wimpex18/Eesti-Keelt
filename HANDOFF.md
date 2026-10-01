# Handoff

Current task: finish source audit and reliable private-material publication.
Branch: `codex/dev-7-corpus-publication`; base: PR #103.

Origin health fingerprints the usable corpus independently of process boot.
The singleton archives changes uploaded to a warm origin; owner health forces
that check and reports corpus_archived_revision for publication confirmation.
Corpus chunks publish through a generation pointer, retaining the previous
archive on interrupted writes. Legacy archives remain readable; learner event
replay and durability gates remain separate. Operator instructions are updated.

Verified: 2,517 Python tests passed, 1 skipped; 224 browser journeys passed,
4 skipped; 22 Worker tests, typecheck and Worker dry-run passed. One startup
visibility assertion passed its focused retry and the next full browser pass.
Prior UI: all 11 tabs in both themes at desktop, phone portrait/landscape and
tablet inspected; actual ERR MP3/HLS and lesson → practice verified on phone/PC.
Private corpus: 506 items, all 461 previous ids retained; 48 HARNO files refreshed.

Next: publish this PR; correct B1 writing's now-unambiguous HARNO 35-minute
clock/two-task description; finish official-PDF visual checks and audit report.
PRs #100 → #101 → #102 → #103 passed CI; user merges in order. No deployment.
Uncommitted paths: Worker/publishing script, corpus health/revision, publication
docs, regression tests and this handoff. Temporary visual test is not staged.
Durable unresolved work: Linear DEV-5 through DEV-9. Latest Python 3.14.8 has
no managed macOS download yet; local 3.14.7, production patch needs attestation.
After merging: publish private corpus/exam files, confirm both corpus hashes
via owner health, then deep smoke. Private data remains git-ignored.
