# Handoff

Current task: beginner exercise guidance for Russian-speaking learners.
Branch: `codex/a1-exercise-guidance`; PR base: `main` (366a35b).
Implemented: explicit Russian instructions, case/person glosses, whole-sentence
Russian support for known personal-pronoun frames, and optional online sentence
translation. Phone sets scroll the first exercise into view without focusing
the keyboard. Grading and signed item identity are unchanged.
Existing Estep name, stepped-E artwork and phone launch motion are already on main.
Verification: 2,467 Python tests passed, 34 skipped; two full-dictionary tests
excluded because this workspace contains a miniature fixture. 131 focused tests
passed after the final edits; typecheck passed.
Browser: 184 passed in the broad run. Its two phone guidance regressions were
fixed; all 12 targeted plan/landscape/translation checks passed. Four broad-run
failures need dictionary examples or multiple corpus bands absent in the fixture.
Screenshots inspected across desktop, phone, landscape and tablet; Impeccable
review approved the scoped exercise extension. Existing design tokens preserved.
Published: https://github.com/wimpex18/Eesti-Keelt/pull/106 (owner merges).
Next: owner merges the exercise PR. Continue public access separately via
`docs/public-access-followup.md` (bootstrap-owner and source-access gates).
Uncommitted paths: none after this commit.
Blocker: no Cloudflare/Google deployment credentials in the current environment;
the live URL still redirects to Cloudflare Access. Public mode is not enabled.
The Linear follow-up remains blocked by automatic approval review; remaining
public-access work is documented in the repository. GitHub publication succeeded.
Local review patch: `.impeccable/review/a1-exercise-guidance.patch`.
