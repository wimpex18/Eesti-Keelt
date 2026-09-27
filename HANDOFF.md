# Handoff

Current task: owner/guest split and the profile page (ADR-0006), branch
`claude/owner-guest-split`, one draft PR for docs, skeletons and the
implementation.

Done (senior pass): decisions in `docs/adr/0006-owner-and-guest.md`; the
file-by-file plan, route classification and profile page spec in
`docs/identity.md`. `eesti/identity.py` and `config.learner_db` are
implemented and tested (`tests/test_identity.py`) but not yet wired into the
app. Skeletons: `eesti/guest.py`, `eesti/profile.py`, `eesti/api/profile.py`
(not registered), `deploy/guest.ts` + `wrangler.jsonc` `env.guest` (not
deployed), `docs/skeletons/profile.js` (not served), and skipped test modules
`tests/test_guest_isolation.py`, `tests/test_profile.py`.

Next step: implement `docs/identity.md` "Origin changes" in order, then the
guest Worker, the profile API and page, the deploy workflow and operator notes.
Unskip the skeleton tests as each part lands.

Validation so far: `pytest tests/ -n auto` and `npm run typecheck` pass;
`wrangler deploy --env guest --dry-run` lists no bindings.
Uncommitted paths: none. Blockers: `GUEST_PROXY_TOKEN` must be created by the
owner on Cloud Run and in repository secrets before the guest Worker can serve.
