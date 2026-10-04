# Handoff

Current task: DEV-17/DEV-18 QA fixes complete locally; prepare review PR.
Branch: codex/dev-17-dev-18-qa-fixes; base origin/main eba54af.
Next: commit named task paths, push and open PR; user reviews and merges.
After deployment: deep smoke and public cold-load/account verification.
Fixed: signed recipient-bound dictation with issued evidence/source rights;
compressed startup bundle/CSS, immediate start content, stable font rendering;
onboarding Back/focus, request deadlines, draft/duplicate recovery, lazy probes,
and 44px navigation/word targets. Provider lanes and linguistic rules unchanged.
Checks: 2544 Python passed/1 skipped; compiled browser 205 passed/23 skipped;
62 focused passed; typecheck and 26 Worker tests passed.
Chrome: prior 15-route/five-viewport audit plus follow-up desktop/phone checks.
Matched local FCP 2.1–2.2→0.8 s; initialization 3.0→1.1 s; JS requests 24→1.
Final mobile Lighthouse CLS 0.003; cursor-extension LCP excluded.
Reports: qa/test-plan.md, inventory.md, results.md, performance.md.
Evidence: .impeccable/review/qa (ignored); synthetic guest state only.
Uncommitted task paths: .github/workflows/tests.yml, .gitignore, Dockerfile,
DESIGN.md, HANDOFF.md, docs/status.md, docs/testing.md, deploy/build-web.mjs,
package.json, package-lock.json, eesti/api/{assets,speech}.py,
eesti/{dictation,itemref}.py, eesti/web/{app.css,index.html},
eesti/web/js/{core,listen,main,onboarding,router,speak,voice,write}.js,
tests/test_{dictation,docs_match_code,e2e_journeys,ui_contract,web_build}.py,
qa/{test-plan,inventory,results,performance}.md.
Preserve unrelated untracked agent/editor tooling. No learner databases or
private exam/evaluation material in the diff; no merge or deployment performed.
Remaining external gates: real Worker account/cross-device durability,
human-verified physical-device ASR/fallback, screen-reader and private materials.
Chrome preview: http://127.0.0.1:8000/?sandbox=qa-final#start.
Preview: /tmp/eesti-qa/run.py, scratch guest state, blank provider keys,
EESTI_WEB_BUILD=1. DEV-5 beginner/en/uk scope remains separate.
