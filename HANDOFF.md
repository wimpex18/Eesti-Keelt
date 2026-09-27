# Handoff

Current task: implement ADR-0006 with isolated learner accounts, guest sandboxes and the Profiil page.

Done: origin, Worker, profile UI, deploy guidance and coverage are implemented. The first account inherits existing progress; later accounts are separate permanent learners, with unlimited sign-up; guests use disposable sandboxes. Browser review covered all four target sizes in light and dark themes.

Next: commit and push `luna/learners-and-guests`, then open the authorized draft PR. The owner adds `SESSION_SECRET` to GitHub Actions secrets before merging; first sign-up creates the owner account.

Uncommitted paths:
.github/workflows/deploy.yml, .gitignore, HANDOFF.md
deploy/accounts.ts, deploy/accounts.check.ts, deploy/reset-account-password.ts, deploy/worker.ts
docs/adr/0006-learners-and-guests.md, docs/app-structure.md, docs/architecture.md, docs/deploy.md, docs/identity.md, docs/status.md, docs/testing.md; removed docs/prompts/learners-guests-luna.md and docs/skeletons/profile.js
eesti/api/__init__.py, eesti/api/deps.py, eesti/api/notion.py, eesti/api/practice.py, eesti/api/profile.py, eesti/api/speech.py, eesti/api/state.py
eesti/app.py, eesti/config.py, eesti/evidence.py, eesti/gloss.py, eesti/guest.py, eesti/identity.py, eesti/licences.py, eesti/mining.py, eesti/planning.py, eesti/profile.py, eesti/providers/budget.py
eesti/web/app.css, eesti/web/index.html, eesti/web/js/main.js, eesti/web/js/profile.js, eesti/web/js/router.js, eesti/web/sw.js
tests/test_accounts.py, tests/test_e2e_journeys.py, tests/test_guest_isolation.py, tests/test_learners.py, tests/test_profile.py, tests/test_ui_contract.py, tests/test_worker_accounts_contract.py; tsconfig.json

Blockers: none. Production account sign-up needs the owner to add `SESSION_SECRET` before merge.
