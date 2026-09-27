# Handoff

Current task: learners, guests and the profile page (ADR-0006). The design
pass is on `main`; the implementation goes on a new branch and PR.

Done (senior pass): decisions in `docs/adr/0006-learners-and-guests.md`; the
file-by-file plan, routes by scope and profile page spec in `docs/identity.md`.
Accounts live in the app: sign-up/sign-in run by the Worker, stored in the
`singleton` Durable Object. The first account is the owner (keeps existing
progress), the second a permanent learner with their own files and object;
not signed in is a throwaway guest sandbox. All material for everyone.
`eesti/identity.py` and `config.learner_db` are implemented and tested
(`tests/test_identity.py`) but not wired into the app. Skeletons: `deploy/accounts.ts`,
`eesti/guest.py`, `eesti/profile.py`, `eesti/api/profile.py` (not
registered), `docs/skeletons/profile.js` (not served), and skipped
`tests/test_guest_isolation.py`, `tests/test_learners.py`,
`tests/test_profile.py`. Brief: `docs/prompts/learners-guests-luna.md`.

Next step: implement `docs/identity.md` "Origin changes" in order, then the
Worker changes, the profile API and page, the deploy workflow and operator
notes. Unskip the skeleton tests as each part lands.

Validation so far: `pytest tests/ -n auto` and `npm run typecheck` pass.
Uncommitted paths: none. Blockers: the owner adds the `SESSION_SECRET` Worker
secret; after merge, the owner signs up first, then the second person.
