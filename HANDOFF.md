# Handoff

Current task: source/materials audit and safe learning improvements.
Branch: `codex/materials-learning`; base: PR #102 (`codex/source-provenance`).

Section browsing now respects offsets with stable round-robin skill coverage.
Listening shelves can load/retry later pages without clearing opened lessons.
Radio notes no longer hardcode counts or promise every lesson has a transcript.
Object-case guidance uses EKI SÜ 38/40: completion may be future; full objects
can be omastav or nimetav; ordinary and contrastive negation are distinguished.
The EKK/Teatmik ledger now describes the attributed rules/forms actually used.

Verified: 2,517 Python tests passed, 1 skipped; 224 browser journeys passed,
4 skipped; 21 Worker tests and typecheck passed. All 11 tabs inspected in both
themes at desktop, phone portrait/landscape and tablet. Real ERR MP3/HLS played
on desktop/phone; the object lesson opens and starts deterministic practice.
Private local corpus: 506 items, all 461 previous ids retained; 48 HARNO files
validated/refreshed. Reference and source map: docs/source-integrations.md.

Next: publish this PR, fix warm-origin corpus archive refresh, complete report.
Durable unresolved coverage/freshness/review work: Linear DEV-5 through DEV-9.
PRs #100 → #101 → #102 are open; user merges in order. No deployment performed.
Uncommitted paths: library/API/listening UI, object lesson/reference, attribution,
tests, source/status docs and this handoff. Private data is git-ignored.
Blocker for production changes: owner merges, then private corpus/media upload
and the deep smoke workflow; the existing archive must retain the new corpus.
