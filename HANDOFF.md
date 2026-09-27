# Handoff

Current task: PR #91 account isolation, profile, backend and design audit is complete.

Branch: `luna/learners-and-guests`; open PR #91.

Done: fixed request-scoped household/guest allowance persistence, hardened account inputs and removal, and corrected profile recovery, focus, tab state, language markup and spacing. Current-state identity, architecture, deployment, testing and status docs match the implementation.

Verification: full suite 2,482 passed, 1 skipped; browser journeys 167 passed, 3 skipped; typecheck, Worker account checks, morphology validation and `git diff --check` passed. Reviewed desktop, tablet, phone and landscape layouts in light and dark themes.

Branch check: `claude/home-asr-binding` is 14 commits behind main and its sole ahead commit is patch-identical to `db8fbfe`, already merged in PR #88. Nothing should be merged from it.

Next: owner reviews and merges PR #91.

Uncommitted paths: none after the audit commit.

Blockers: none.
