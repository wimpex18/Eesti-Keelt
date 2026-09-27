# Implementation prompt: learners, guests and profile (GPT-6 Luna, xhigh)

Paste everything below the line into the implementer's session.

---

You are implementing an already-decided change in the Eesti-Keelt repository
(Estonian exam prep; FastAPI + SQLite on Cloud Run behind a Cloudflare Worker;
plain HTML/CSS/JS, no build step). The architecture is decided. Your job is to
implement it exactly, test it, and hand off. Do not redesign.

## Task

Implement ADR-0006. Accounts live in the app: a sign-up / sign-in page, run by
the Worker, with accounts stored in the `singleton` Durable Object. The first
account is the owner and inherits all existing progress; the second (capped by
`MAX_ACCOUNTS`, default 2) is a permanent learner with their own files and
Durable Object. Anyone not signed in (Claude, Codex, tests) gets the full app
with all material in a throwaway sandbox and must never sign up. A Profile page
shows each person's progress. Cloudflare Access stays exactly as it is.

## Read first, in this order (they are authoritative)

1. `AGENTS.md`, `HANDOFF.md`, `.claude/rules/*.md` (path rules for Python, web,
   tests, docs, deploy).
2. `docs/adr/0006-learners-and-guests.md` (the decisions and why).
3. `docs/identity.md` (the specification, file by file). Follow its order.
4. `docs/adr/0005-architecture-contracts.md` (contracts you must not break).
5. `DESIGN.md` "Adding a page or section", "Layout rhythm", "Signature
   components" (Seals, Rütm) before touching the page.
6. The code already on `main`: `eesti/identity.py`, `config.learner_db`,
   `tests/test_identity.py` (done), and the skeletons `deploy/accounts.ts`,
   `eesti/guest.py`,
   `eesti/profile.py`, `eesti/api/profile.py`, `docs/skeletons/profile.js`,
   `tests/test_guest_isolation.py`, `tests/test_learners.py`,
   `tests/test_profile.py`.

## Rules

- The design PR is merged. Branch `luna/learners-and-guests` from the latest
  `main`, push it, and open one draft PR for all of this work. Stage named
  paths only; never `git commit -a`. Do not merge.
- Replace every `TODO(Luna)` and `NotImplementedError`. Keep the signatures
  and response shapes written in the skeletons; if one is wrong, fix it and the
  spec together and say why in the PR.
- If the spec and the code disagree, the code's existing contracts (ADR-0005)
  win; change `docs/identity.md` to match and note it in `HANDOFF.md`.
- No new framework, database engine, service, dependency, CSS colour, shadow,
  card style or glass surface. Reuse `sealsHtml`, `rhythmHtml`, `ruCount`,
  `setLabel`, `retryableError`, the tablist pattern and existing tokens.
- UI labels Estonian, explanations Russian (natural Russian, not calqued),
  `lang` attributes as `eesti/web/js/core.js` describes. No streak or score.
- Never change owner behaviour: an owner request with the old headers must
  behave exactly as today, including restore, snapshots and `x-events-seq`.
  The owner's file paths and the `singleton` Durable Object keep their names.
- Do not deploy, create secrets, or change Cloudflare/Google settings. Write the
  operator steps into `docs/deploy.md` instead.
- Keep tests offline (`tests/test_offline.py`). No real credentials anywhere.
- Never sign up or sign in on the deployed app yourself; test as a guest there.

## Acceptance criteria

1. **Isolation.** Every test in `tests/test_guest_isolation.py` is implemented
   and passes: a guest answer changes no owner file byte; owner and guest (and
   two sandboxes) see only their own progress; guest responses have no
   `x-events-seq`; the guest log needs no restore; snapshot/event export carry
   owner rows only; a guest sees the same material as the owner; every route
   is classified by scope; the back channel refuses guest scope; guest
   allowances are shared and smaller; `POST /api/guest/reset`
   works for a guest and is 403 for the owner; sweeping drops idle and surplus
   sandboxes.
2. **Learners.** Every test in `tests/test_learners.py` is implemented and
   passes: two permanent learners never see each other's progress; each has
   their own back channel, restore and `x-events-seq`; a new learner gets one
   `joined` event; owner-only actions are refused; the allowance is shared.
3. **Worker and accounts.** `deploy/accounts.ts` and `deploy/worker.ts` per
   `docs/identity.md` "Worker changes": `/api/auth/signup|login|logout|me` with
   PBKDF2 hashes and an HMAC-signed `HttpOnly` session cookie; sign-up closes at
   `MAX_ACCOUNTS`; the first account is `owner`; caller-sent `x-eesti-*` scope
   headers are stripped and set from the session; no session is a guest once
   an account exists (before that, and without `SESSION_SECRET`, everything is
   the owner, as today); one `LearnerState` per permanent learner (`singleton`
   for the owner, `learner:<id>`) sending its scope on every back-channel call;
   corpus sync in `singleton` only; guests have no object and get 403 on
   `/api/push/*`; the cron reminds both learners. `npm run typecheck` passes; a
   test pins these rules the way `tests/test_origin_guard.py` reads
   `deploy/worker.ts`, and the auth helpers are exercised under Node as
   `deploy/push.check.ts` is; checked with `wrangler dev`: sign up twice, sign
   out, each lands in its own files.
4. **Profile API.** `GET /api/me` and `POST /api/me` return the shape in
   `eesti/profile.py`; every test in `tests/test_profile.py` is implemented and
   passes, including strict replay of `profile-set`.
5. **Profile page** (a required deliverable, not polish). A `Profiil` tab in the
   Eksam mode with: editable name (Muuda / Salvesta / Loobu), email, *Õpib
   alates*, *Viimati*, level (current, exam goal, checkpoints), seals per level
   with an A1/A2/B1 tablist, Rütm, totals, which account is signed in
   (*Põhikonto*, *Õppija* or *Külaline*) with *Logi välja*, for guests the
   sign-in / sign-up views (*Logi sisse*, *Loo konto*: e-mail, password, name),
   the sandbox line on every screen and *Tühjenda liivakast*. Checked in a real browser at
   1440×900, 402×874 and 874×402 (touch), 744×1133 (touch), light and dark:
   screenshots looked at, no horizontal scroll, targets ≥44px, nothing
   clipped. `docs/app-structure.md` lists the tab.
6. **Journeys.** `tests/test_e2e_journeys.py` covers the profile (view, rename,
   sign-up, sign-in, sign-out, guest line, reset) and runs its progress-writing journeys in a guest
   sandbox; `pytest tests/test_e2e_journeys.py --browser -q` passes.
7. **Deploy path.** `.github/workflows/deploy.yml` pushes the
   `SESSION_SECRET` Worker secret and warns (does not fail) when it is missing;
   `docs/deploy.md` has, without any value, how to create it, the first-use
   order (the owner signs up first and inherits the progress, then the second
   person), and the operator steps for a forgotten password or removing an
   account.
8. **Docs.** `docs/architecture.md` (request path, API and domain module
   tables), `docs/status.md` (replace the "Tests and agents write into the
   owner's log" known issue with what works now and what remains, and the
   single-learner wording anywhere it is now wrong),
   `docs/identity.md` matches the code, `docs/skeletons/` deleted after the page
   module moves to `eesti/web/js/profile.js`. `AGENTS.md` stays under 100 lines.
9. **Suite.** `python -m pytest tests/ -q -n auto` and `npm run typecheck` pass
   with no new skips except ones that already skip for missing local data.

## Validation before you stop

Run the full suite, the typecheck, `npx wrangler deploy --dry-run` and the
browser journeys; take the screenshots in criterion 5 and inspect them. Then re-read
`docs/identity.md` "Routes by scope" against `eesti.api.paths()` once
more: a route added since is unclassified until you classify it.

## Hand-off

Rewrite `HANDOFF.md` as the present-state note `AGENTS.md` asks for (≤30
lines): what is done, the exact next step (the owner adds `SESSION_SECRET`,
merges, then signs up first), uncommitted paths,
blockers. Update the PR description with Before/After and the validation you ran. Stop there; do not
merge or deploy.

If something cannot be done without violating a rule above (for example the
context variable does not reach sync routes, or WebCrypto PBKDF2 is
unavailable in the Workers runtime), stop that part, leave the test that shows
it failing as `xfail` with the reason, and record it under Blockers in
`HANDOFF.md` rather than inventing a workaround.
