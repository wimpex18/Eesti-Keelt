# Handoff

Current task: DEV-17/DEV-18 fixes ready for user review in PR 110.
Branch: codex/dev-17-dev-18-qa-fixes; base origin/main eba54af.
PR: https://github.com/wimpex18/Eesti-Keelt/pull/110
Next: user reviews/merges; after deployment run deep smoke and public
cold-load/account verification. No merge or deployment performed here.
Fixed: signed recipient-bound dictation with issued evidence/source rights;
compressed startup bundle/CSS, immediate start content, stable font rendering;
onboarding Back/focus, request deadlines, draft/duplicate recovery, lazy probes,
and 44px navigation/word targets. Provider lanes and linguistic rules unchanged.
Checks: 2544 Python passed/1 skipped; compiled browser 205 passed/23 skipped;
62 focused passed; typecheck and 26 Worker tests passed. Docker not built locally.
Chrome: initial 15-route/five-viewport audit plus follow-up desktop/phone checks.
Matched local FCP 2.1–2.2→0.8 s; initialization 3.0→1.1 s; JS requests 24→1.
Final mobile Lighthouse CLS 0.003; cursor-extension LCP excluded.
Reports: qa/test-plan.md, inventory.md, results.md, performance.md.
Evidence: .impeccable/review/qa (ignored); synthetic guest state only.
Uncommitted task path before this handoff commit: HANDOFF.md only.
After this handoff commit: no uncommitted task paths. Preserve unrelated
untracked agent/editor tooling. No learner databases or private exam/evaluation
material in the diff.
Remaining external gates: real Worker account/cross-device durability,
human-verified physical-device ASR/fallback, screen-reader and private materials.
Chrome preview: http://127.0.0.1:8000/?sandbox=qa-final#start.
Preview: /tmp/eesti-qa/run.py, scratch guest state, blank provider keys,
EESTI_WEB_BUILD=1. DEV-5 beginner/en/uk scope remains separate.
