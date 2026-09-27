# ADR-0006: Owner and guest

**Status:** Accepted, implementation in progress (`docs/identity.md`).
**Scope:** one owner, a testing account and agents as throwaway guests, one
origin, everything behind Cloudflare Access.

## Problem

The app has one evidence log. The owner's real study, the owner's own
exploratory clicks, Claude/Codex browser runs and journey tests all write into
it, and replay turns every one of those events into mastery, FSRS cards and
readiness. Nothing can tell them apart afterwards.

## Decision

Two scopes, decided by the Access identity at the front door, never by the page:

| Scope | Who | Access identity | Stores | Lifetime |
|---|---|---|---|---|
| `owner` | the owner | email equal to `OWNER_EMAIL` | `data/*.db` (today's files) | permanent: Durable Object log and snapshots |
| `guest` | the owner's testing account, Claude/Codex, tests | any other email, or a service token | `data/guest/<sandbox>/*.db` | the container's disk: gone on a cold start, on reset, or after 24 h idle |

1. **One Worker, one front door.** Access stays on for everyone; there are no
   public guests. The owner allows two accounts in the Access policy (and, for
   headless agents, optionally a service token). The Worker reads
   `ctx.access.getIdentity()` and sends the origin `x-eesti-scope` and
   `x-eesti-email`, after deleting any the caller sent. With `OWNER_EMAIL`
   unset it sends no scope, and everything stays owner, exactly as today.
2. **The origin trusts the scope only from the Worker.** `x-eesti-scope` is read
   only on a request carrying `PROXY_TOKEN`. A request with none is the owner
   (the old Worker). Locally (`cli serve`, tests) the guard is off and the same
   header or `EESTI_SCOPE` chooses; default owner (`eesti/identity.py`).
3. **One process, request-scoped paths.** Learner database paths are resolved
   per request through `config.learner_db(name)`, which reads the request's
   scope from a context variable. `config.PROGRESS_DB` and friends stay the
   owner paths, so the CLI, the snapshot routes and the existing tests are
   unchanged. No second service, database engine or framework.
4. **Guest sandboxes are per caller.** A guest request names its sandbox with
   `x-eesti-guest` (agents and tests pick a readable name) or keeps the
   `eesti_guest` cookie set on first contact. Two agents at once do not see each
   other's progress. At most 50 sandboxes; oldest idle dropped first; any idle
   for 24 h dropped.
5. **Guest writes never reach the owner's permanence.** For a guest the origin
   omits `x-events-seq`, so the Worker never copies guest events; snapshots and
   `/api/events` export the owner's files only; a guest log starts with its own
   backfill marker, so the restore gate (`NotRestored`) never applies to it.
   The Worker answers `/api/push/*` itself from the owner's Durable Object, so
   it refuses those to a guest.
6. **Guests see everything the owner sees.** All material is licensed for the
   owner's private study and every guest is behind the owner's Access, so there
   is no licence gating by scope. Speech, tutor and grammar lanes work the same.
7. **Guests have their own allowances.** Budget counters for guest scope live in
   `data/guest/shared.db`, one store for all sandboxes, with `budget.GUEST_CAPS`
   (below the owner's caps: the Workers AI allocation is shared). Speech via the
   Worker is not counted by Python, as today.
8. **Nothing leaves the app from a sandbox.** Guests never push to the Notion
   `Vead` log, never write the owner's private speech eval set, never subscribe
   to reminders.
9. **The profile is derived from the log, not a new store.** `GET /api/me`
   reports name, email, first and last activity, level, milestones and rhythm;
   `POST /api/me` records a `profile-set` event (the name). Email is the Access
   identity on each request. The app has no streak and adds none: *Rütm* is the
   rhythm (`DESIGN.md`: nothing resets). A guest has its own profile in its
   sandbox, which is how agents test the page.

## Contracts to preserve

- Owner behaviour is unchanged while `OWNER_EMAIL` is unset and for any request
  without `x-eesti-scope`.
- Event envelopes keep `learner`; owner events stay `owner`, guest events are
  `guest:<sandbox>`. `profile-set` is registered with a no-op apply so strict
  replay (`cli verify-backup`) accepts it.
- Stable route contracts, signed item refs and offline queue IDs (ADR-0005).
- No new persistence source: the profile name lives in the log.

## Alternatives rejected

- **A second, Access-free guest Worker.** Would expose owner-only material
  publicly and need a second secret and deploy; the owner has no public guests.
- **Per-identity Durable Objects** (ADR-0005, still deferred). The origin is the
  single writer; naming more objects would not isolate its SQLite files.
- **A second Cloud Run service for guests.** Doubles cold starts and builds for
  isolation a directory gives.
- **Marking guest events inside the owner log and filtering on replay.** Every
  projection, readiness and planner query would need the filter forever; one
  missed query leaks test data into mastery.

## Residual risks

- **Misconfiguration fails towards pollution, not exposure.** With `OWNER_EMAIL`
  unset or misspelt, the owner's own account becomes a guest (typo) or every
  account is the owner (unset). The deploy workflow warns when it is unset, and
  the profile shows the scope so the owner can see which one they are in.
- **Headless agents need an Access credential.** A browser agent must sign in as
  the testing account; a script can use an Access service token. Either is a
  credential the owner creates and gives through the agent's environment,
  never chat. `ctx.access.getIdentity()` for a service token has no email;
  that is still a guest.
- **Guest counters reset on a cold start**, so the guest allowance is a per-boot
  ceiling. Guests share the one Workers AI allocation with the owner.
- **Guest and owner share one origin process.** A heavy test run slows the owner.
- **Owner's past test activity stays in the log.** This change stops new
  pollution; it does not clean history. Cleaning is a separate, owner-approved
  operation (export, filter, `cli verify-backup`, restore) not built here.
- **Email trust rests on the Worker.** The origin accepts `x-eesti-scope` and
  `x-eesti-email` only with `PROXY_TOKEN`; a leaked `PROXY_TOKEN` already grants
  owner access.
