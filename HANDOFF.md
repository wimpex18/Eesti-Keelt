# Handoff

Current task: implement ADR-0006 with isolated learner accounts, guest sandboxes and the Profiil page.

Done: the first account inherits existing progress; all later accounts are separate permanent learners. Sign-up is unlimited. Guests use disposable sandboxes. Profile UI, API, Worker auth and operator guidance are complete.

Draft PR: [#91](https://github.com/wimpex18/Eesti-Keelt/pull/91), branch `luna/learners-and-guests`.

Next: the owner adds `SESSION_SECRET` under repository Settings → Secrets and variables → Actions, reviews and merges PR #91, then creates the first account as owner.

Uncommitted paths: none after this handoff update is committed.

Blockers: owner must add `SESSION_SECRET` before production sign-up and sign-in will work.
