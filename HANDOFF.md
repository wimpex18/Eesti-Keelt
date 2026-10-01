# Handoff

Current task: source audit and B1 exam-format correction, ready for review.
Branch: `codex/harno-writing-clock`; base: PR #104.

B1 writing uses HARNO's 35-minute clock and describes both official tasks.
The mock explicitly practises one longer text over the whole part's clock.
Source/store/UI map: docs/source-integrations.md; feature gaps: docs/status.md.
Private corpus has 506 items, all 461 old ids retained; 48 HARNO files refreshed.
It remains local/git-ignored; learner progress and model lanes are unchanged.

Verified: 2,519 Python tests passed, 1 skipped; 224 browser journeys passed,
4 skipped; 22 Worker tests, typecheck and Worker dry-run passed. Speech-save
journey timed out once, then passed both focused engines and the full rerun.
All 11 tabs/both themes inspected in four viewports; desktop/phone MP3/HLS,
object-case lesson → practice, official A2/B1 forms and B1 timer checked.
PRs #100 → #101 → #102 → #103 → #104 → #105 are open; user merges in order.
Uncommitted paths after this commit: none. Temporary visual tests removed;
private corpus/media remain ignored. No code deployment/private upload.

Next: user merges the stack in order after CI; publish private corpus/exam files,
confirm equal non-null origin/archive corpus hashes in owner health, then run
smoke with deep: true. Current production's guest-material smoke failed;
post-merge deployment and deep verification remain pending.
Durable gaps: Linear DEV-5–DEV-9 (multilingual/A0, native exams, refresh,
linguistic review, corpus-backed CI). Local Python 3.14.7; no managed macOS
3.14.8 download yet. Production patch/input hashes need new health attestation.
Audit evidence/report: source-audit under this chat's visualization directory.
