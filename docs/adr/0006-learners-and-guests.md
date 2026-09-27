# ADR-0006: Learners and guests

**Status:** Accepted, implementation in progress (`docs/identity.md`).
**Scope:** a household of permanent learners (the owner and a second person),
throwaway guests for tests and agents, one origin, everything behind Cloudflare
Access. Supersedes ADR-0005's deferral of per-identity Durable Objects: there is
now a real second learner.

## Problem

The app has one evidence log. The owner's real study, the owner's exploratory
clicks, Claude/Codex browser runs and journey tests all write into it, and
replay turns every event into mastery, FSRS cards and readiness. A second
person in the household, also preparing for the exam, has nowhere of her own
to study.

## Decision

Three scopes, decided by the Access identity at the Worker, never by the page:

| Scope | Who | Access identity | Origin files | Durable Object | Lifetime |
|---|---|---|---|---|---|
| `owner` | the owner | email = `OWNER_EMAIL` | `data/*.db` (today's paths) | `singleton` (today's) | permanent |
| `learner` | another household learner | email in `LEARNER_EMAILS` | `data/learners/<id>/*.db` | `learner:<id>` | permanent |
| `guest` | testing account, Claude/Codex, tests | any other email, or a service token | `data/guest/<sandbox>/*.db` | none | throwaway: cold start, reset, 24 h idle |

`<id>` is `identity.learner_id(email)`: `l-` and the first 16 hex digits of
SHA-256 of the lower-cased email. The Worker and the origin compute the same.

1. **Access is the account system.** Only identities the Access policy allows
   can reach the app. Creating an account is: the owner adds the person's email
   to the Access policy and to `LEARNER_EMAILS`; the person signs in with a
   one-time PIN; the app records `joined` and creates their store. There is no
   password, sign-up form or user table in the app.
2. **The Worker sends the scope; the origin trusts it only with `PROXY_TOKEN`.**
   The Worker reads `ctx.access.getIdentity()`, deletes any caller-sent
   `x-eesti-scope`/`x-eesti-email`, and sets them. A request with no scope
   header is the owner (an older Worker, or `OWNER_EMAIL` unset), so today's
   behaviour is the default. Locally the guard is off and the same headers or
   `EESTI_SCOPE` choose (`eesti/identity.py`).
3. **One process, request-scoped paths.** Learner database paths are resolved
   per request by `config.learner_db(name)` from a context variable. The owner's
   paths are unchanged, so the CLI and existing tests keep working. No second
   service, database engine or framework.
4. **One Durable Object per permanent learner.** Each holds that learner's event
   log, snapshot and push subscriptions, and restores that learner into a fresh
   origin independently: the existing `LearnerState` class, named per learner.
   The owner's object keeps the name `singleton`, so nothing migrates. The
   harvested corpus stays in `singleton` only. The back-channel calls a learner's
   object makes carry that learner's scope headers, so the origin's snapshot and
   event routes read and write that learner's files.
5. **Guest sandboxes are per caller** (`x-eesti-guest`, or the `eesti_guest`
   cookie), at most 50, dropped after 24 h idle. A guest has no Durable Object:
   the origin omits `x-events-seq`, the back channel refuses guest scope, and a
   guest log starts with its own backfill marker, so `NotRestored` never applies.
6. **Everyone sees all material.** Everything is licensed for private study and
   everyone is behind the owner's Access. No gating by scope.
7. **Allowances are per household, not per person.** All permanent learners
   count provider calls in the owner's `progress.db` (the caps protect one
   shared Workers AI allocation); guests count in `data/guest/shared.db` with
   smaller `budget.GUEST_CAPS`.
8. **Some things stay the owner's.** The Notion `Vead` log (the owner's
   workspace) and the private speech eval set (the owner's voice) are owner-only;
   a learner or guest can queue corrections, which stay in their own store.
   Reminders work for every permanent learner through their own object; the
   hourly cron visits each. Guests get none.
9. **The profile is derived from the log.** `GET /api/me` reports name, email,
   registration (`joined`, else the first event), last activity, level,
   milestones and rhythm for the caller; `POST /api/me` records `profile-set`.
   No streak is added (`DESIGN.md`: nothing resets).

## Contracts to preserve

- The owner's paths, Durable Object name, event ids and snapshots are unchanged;
  with `OWNER_EMAIL` unset every request is the owner, as today.
- Event envelopes keep `learner`: `owner`, `l-<hex>`, or `guest:<sandbox>`.
  `profile-set` and `joined` are registered with a no-op apply so strict replay
  (`cli verify-backup`) accepts them.
- Stable route contracts, signed item refs and offline queue IDs (ADR-0005).
- One origin instance, one process. More learners multiply stores, not
  instances.

## Alternatives rejected

- **A separate deployment per person.** Doubles builds, cold starts and secrets
  for two people sharing a flat.
- **One log with a learner column filtered on replay.** Every projection,
  readiness and planner query would need the filter forever; one missed query
  mixes two people's mastery.
- **A user table and sign-up in the app.** Duplicates Access, which already
  proves who is there and already guards the owner-only material.
- **A public guest door.** No one outside the household uses the app.

## Residual risks

- **Misconfiguration fails towards the wrong scope, not exposure.** A misspelt
  `OWNER_EMAIL` makes the owner a guest; a person missing from `LEARNER_EMAILS`
  studies in a throwaway sandbox and loses it. The profile shows the scope
  (*Põhikonto*, *Õppija*, *Külaline*) so it is visible at once, and the deploy
  workflow warns when `OWNER_EMAIL` is unset.
- **Removing someone from `LEARNER_EMAILS` does not delete them.** Their Durable
  Object and files stay until an operator erases them (the procedure in
  `docs/deploy.md` applies per learner). Changing someone's email changes their
  id: moving their history is a manual export and import.
- **A cold start restores every learner who shows up.** Each first request per
  learner waits for that learner's restore; two learners at once mean two
  restores into one instance.
- **One process for everyone.** A heavy test run slows both learners; the
  household allowance can be spent by one person.
- **Headless agents need an Access credential**: the testing account in a
  browser, or a service token in the agent's environment, never in chat.
- **Past test activity stays in the owner's log.** This stops new pollution; it
  does not clean history.
- **Email trust rests on the Worker.** The origin accepts scope and email only
  with `PROXY_TOKEN`; a leaked `PROXY_TOKEN` already grants owner access.
