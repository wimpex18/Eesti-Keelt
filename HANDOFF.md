# Handoff

Current state: `main` holds the October 2026 review work — correctness fixes
(DEV-35), public EVS practice pools (DEV-54), data safety and locked
dependencies (DEV-37, DEV-39) — plus a follow-up on `main`: EVS inflection
types per homograph, retired rection cards out of due counts, one-reading case
labels and fast themed pools for public learners, EKI credit on read-aloud,
level-aware mocks, faster tests and CI (`docs/testing.md`), clearer backup and
public-access errors.
Roadmap and decisions: `qa/architecture-review.md`. Known issues:
`docs/status.md`. Next session: paste the prompt in `qa/next-session.md`
(DEV-40 course structure). One session at a time, one branch and one PR.

Owner actions before anything else (details in `qa/architecture-review.md`):
1. Remove the Cloudflare Access login on the `workers.dev` hostname; rerun
   `deploy`; run `smoke` with `deep: true`.
2. Cloud Shell: `deploy/set-item-secret.sh`, `deploy/setup-backup.sh`,
   `deploy/check-service.sh`.
3. Allow GitHub Actions to create pull requests (weekly lock upgrade).
4. Mac mini: rerun `deploy/home-asr/install.sh` from the new ZIP.
5. Send `qa/source-permission-requests.md` from the project's address.
6. `ANTHROPIC_API_KEY` in `.env` before DEV-38.

Uncommitted task paths: none after this commit. Preserve unrelated untracked
agent/editor tooling. No learner data in the diff. Blockers: the Access login
(1) keeps the public app unreachable and `deploy`/`smoke` red.
