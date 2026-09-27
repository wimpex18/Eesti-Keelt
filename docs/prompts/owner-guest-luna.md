# Implementation prompt: owner/guest split and profile (GPT-6 Luna, xhigh)

Paste everything below the line into the implementer's session.

---

You are implementing an already-decided change in the Eesti-Keelt repository
(Estonian exam prep; FastAPI + SQLite on Cloud Run behind a Cloudflare Worker;
plain HTML/CSS/JS, no build step). The architecture is decided. Your job is to
implement it exactly, test it, and hand off. Do not redesign.

## Task

Implement ADR-0006: the owner's Access account keeps permanent progress; any
other Access identity (the owner's testing account, Claude/Codex, tests) gets
the full app with all material in a separate, throwaway sandbox; and a Profile
page shows the learner's progress.

## Read first, in this order (they are authoritative)

1. `AGENTS.md`, `HANDOFF.md`, `.claude/rules/*.md` (path rules for Python, web,
   tests, docs, deploy).
2. `docs/adr/0006-owner-and-guest.md` (the decisions and why).
3. `docs/identity.md` (the specification, file by file). Follow its order.
4. `docs/adr/0005-architecture-contracts.md` (contracts you must not break).
5. `DESIGN.md` "Adding a page or section", "Layout rhythm", "Signature
   components" (Seals, Rütm) before touching the page.
6. The code already on the branch: `eesti/identity.py`, `config.learner_db`,
   `tests/test_identity.py` (done), and the skeletons `eesti/guest.py`,
   `eesti/profile.py`, `eesti/api/profile.py`, `docs/skeletons/profile.js`,
   `tests/test_guest_isolation.py`, `tests/test_profile.py`.

## Rules

- Work on branch `claude/owner-guest-split`; push to it so the existing draft
  PR updates. Stage named paths only; never `git commit -a`. Do not merge.
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
- Do not deploy, create secrets, or change Cloudflare/Google settings. Write the
  operator steps into `docs/deploy.md` instead.
- Keep tests offline (`tests/test_offline.py`). No real credentials anywhere.

## Acceptance criteria

1. **Isolation.** Every test in `tests/test_guest_isolation.py` is implemented
   and passes: a guest answer changes no owner file byte; owner and guest (and
   two sandboxes) see only their own progress; guest responses have no
   `x-events-seq`; the guest log needs no restore; snapshot/event export carry
   owner rows only; a guest sees the same material as the owner; every route
   is classified; Notion push, eval and reminder settings are refused to a
   guest; guest allowances are shared and smaller; `POST /api/guest/reset`
   works for a guest and is 403 for the owner; sweeping drops idle and surplus
   sandboxes.
2. **Worker.** `deploy/worker.ts` per `docs/identity.md` "Worker changes":
   strips caller-sent `x-eesti-scope`/`x-eesti-email`, derives the scope from
   `ctx.access.getIdentity()` and `OWNER_EMAIL` (unset: no headers, behaviour
   as today), refuses `/api/push/*` to a guest, skips snapshot/pull for a
   guest, and forwards the scope on the speech path. `npm run typecheck`
   passes; a test reads `deploy/worker.ts` as `tests/test_origin_guard.py`
   does and pins these rules; checked with `wrangler dev` and
   `access.dev.identity` as the owner and as another email.
3. **Profile API.** `GET /api/me` and `POST /api/me` return the shape in
   `eesti/profile.py`; every test in `tests/test_profile.py` is implemented and
   passes, including strict replay of `profile-set`.
4. **Profile page** (a required deliverable, not polish). A `Profiil` tab in the
   Eksam mode with: editable name (Muuda / Salvesta / Loobu), email, *Õpib
   alates*, *Viimati*, level (current, exam goal, checkpoints), seals per level
   with an A1/A2/B1 tablist, Rütm, totals, which account is signed in
   (*Põhikonto* or *Külaline*), and for guests the sandbox line on every screen
   plus *Tühjenda liivakast*. Checked in a real browser at
   1440×900, 402×874 and 874×402 (touch), 744×1133 (touch), light and dark:
   screenshots looked at, no horizontal scroll, targets ≥44px, nothing
   clipped. `docs/app-structure.md` lists the tab.
5. **Journeys.** `tests/test_e2e_journeys.py` covers the profile (view, rename,
   guest line, reset) and runs its progress-writing journeys in a guest
   sandbox; `pytest tests/test_e2e_journeys.py --browser -q` passes.
6. **Deploy path.** `.github/workflows/deploy.yml` pushes the `OWNER_EMAIL`
   Worker secret and warns (does not fail) when it is missing;
   `docs/deploy.md` has the owner's one-time steps (the `OWNER_EMAIL` secret,
   the testing account in the Access policy, an optional service token for
   headless agents) without any value.
7. **Docs.** `docs/architecture.md` (request path, API and domain module
   tables), `docs/status.md` (replace the "Tests and agents write into the
   owner's log" known issue with what works now and what remains),
   `docs/identity.md` matches the code, `docs/skeletons/` deleted after the page
   module moves to `eesti/web/js/profile.js`. `AGENTS.md` stays under 100 lines.
8. **Suite.** `python -m pytest tests/ -q -n auto` and `npm run typecheck` pass
   with no new skips except ones that already skip for missing local data.

## Validation before you stop

Run the full suite, the typecheck, both wrangler dry runs and the browser
journeys; take the screenshots in criterion 4 and inspect them. Then re-read
`docs/identity.md` "Routes for a guest" against `eesti.api.paths()` once
more: a route added since is unclassified until you classify it.

## Hand-off

Rewrite `HANDOFF.md` as the present-state note `AGENTS.md` asks for (≤30
lines): what is done, the exact next step (the owner sets `OWNER_EMAIL` and
adds the testing account to Access, then merges), uncommitted paths, blockers. Update the PR
description with Before/After and the validation you ran. Stop there; do not
merge or deploy.

If something cannot be done without violating a rule above (for example the
context variable does not reach sync routes, or an owner-only route cannot be
gated without changing its contract), stop that part, leave the test that shows
it failing as `xfail` with the reason, and record it under Blockers in
`HANDOFF.md` rather than inventing a workaround.
