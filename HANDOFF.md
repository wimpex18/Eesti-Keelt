# Handoff

Current task: learners, guests and the profile page (ADR-0006), branch
`claude/owner-guest-split`, one draft PR for docs, skeletons and the
implementation.

Done (senior pass): decisions in `docs/adr/0006-learners-and-guests.md`; the
file-by-file plan, routes by scope and profile page spec in `docs/identity.md`.
Access is the account system: the owner's email and each `LEARNER_EMAILS`
address are permanent learners with their own files and Durable Object; any
other Access identity is a throwaway guest sandbox. All material for everyone.
`eesti/identity.py` and `config.learner_db` are implemented and tested
(`tests/test_identity.py`) but not wired into the app. Skeletons:
`eesti/guest.py`, `eesti/profile.py`, `eesti/api/profile.py` (not
registered), `docs/skeletons/profile.js` (not served), and skipped
`tests/test_guest_isolation.py`, `tests/test_learners.py`,
`tests/test_profile.py`. Brief: `docs/prompts/learners-guests-luna.md`.

Next step: implement `docs/identity.md` "Origin changes" in order, then the
Worker changes, the profile API and page, the deploy workflow and operator
notes. Unskip the skeleton tests as each part lands.

Validation so far: `pytest tests/ -n auto` and `npm run typecheck` pass.
Uncommitted paths: none. Blockers: the owner sets the `OWNER_EMAIL` and
`LEARNER_EMAILS` Worker secrets and adds those emails and a testing account to
the Access policy before learners and guests work.
