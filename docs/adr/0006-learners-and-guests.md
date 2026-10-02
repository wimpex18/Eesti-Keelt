# ADR-0006: Learners and guests

**Status:** Accepted and implemented (`docs/identity.md`).
**Scope:** public entry, optional in-app accounts, isolated guests and one origin.
This supersedes ADR-0005's deferral of per-identity Durable Objects.

## Problem

The app had one evidence log. Real study, exploratory clicks and agent runs all
wrote into it and counted as mastery, FSRS cards and readiness. Other people in
the household needed their own progress.

## Decision

Grove opens publicly. Accounts live in the app and are optional.

| Scope | Who | How | Origin files | Durable Object | Lifetime |
|---|---|---|---|---|---|
| `owner` | operator-provisioned identity | signed in | `data/*.db` (today's paths) | `singleton` (today's) | permanent |
| `learner` | public sign-up | signed in | `data/learners/<id>/*.db` | `learner:<id>` | permanent |
| `guest` | anyone not signed in | no session | `data/guest/<sandbox>/*.db` | none | throwaway: cold start, reset, 24 h idle |

1. **Sign-up and sign-in in the app, owned by the Worker.** Accounts (id,
   email, password hash, created) live in the `singleton` Durable Object's SQL
   store, so they are permanent and never on Cloud Run's ephemeral disk. The
   Worker answers the account routes itself, as it does `/api/push/*`.
   Passwords are 10–1024 characters and use PBKDF2-SHA-256 (WebCrypto, 100 000
   iterations, per-account salt); email addresses are limited to 254
   characters. The session is an `HttpOnly`, `Secure`, `SameSite=Lax` cookie
   holding the account id and expiry, signed with `SESSION_SECRET`; it lasts
   90 days.
2. **Public sign-up creates learners.** IDs use `l-` plus 16 random hex digits.
   The owner is provisioned separately through a `STATE_TOKEN`-protected route;
   existing owner credentials, progress and snapshots remain valid.
3. **Not signed in is a guest.** Missing secrets, an empty account registry and
   invalid cookies all remain guest scope. Sandboxes use `x-eesti-guest` or the
   `eesti_guest` cookie and expire after 24 hours idle or a cold start.
4. **The Worker tells the origin who it is.** It deletes caller-sent
   `x-eesti-scope`, `x-eesti-learner` and `x-eesti-email`, then sets them from
   the session. The origin trusts them only with `PROXY_TOKEN`. No scope header
   retains owner compatibility for trusted operator calls (`eesti/identity.py`);
   the public Worker always sends an explicit scope.
5. **One process, request-scoped paths** via `config.learner_db(name)`. The
   owner's paths are unchanged; no new service, engine or framework.
6. **One Durable Object per permanent learner:** the existing `LearnerState`
   class is named per account, and holds that learner's log, snapshot and push
   subscriptions. Back-channel calls carry the learner's scope headers. The
   corpus stays in `singleton`. Guests have no object, no `x-events-seq`, and
   their logs receive their own backfill marker.
7. **Public corpus visibility.** Nonowner content connections expose only
   publicly shareable source items, including direct IDs, files and derived drills.
   Owner imports remain in the owner’s library.
8. **Owner only:** the Notion `Vead` push and private speech eval set. Reminders
   belong to each permanent account; guests cannot subscribe.
9. **One shared allowance** for provider calls (the owner's `progress.db`);
   guests count in `data/guest/shared.db` with smaller `GUEST_CAPS`.
10. **Profile from the log.** Name (`profile-set`, editable), optional starting
    recommendation (`onboarding-set`, self-assessment only), email (from the
    account), registration (`joined`), activity, level, milestones and rhythm.
    No streak.

## Contracts to preserve

- Unsigned requests always use guest scope. An explicit valid sandbox also
  selects guest scope for signed-in accounts.
- The owner's paths, `singleton` object, event ids and snapshots are unchanged.
- Event `learner`: `owner`, `l-<hex>`, or `guest:<sandbox>`; `profile-set`,
  `onboarding-set` and `joined` have no-op applies so strict replay accepts them.
- ADR-0005 route contracts, signed item refs and offline queue IDs.

## Alternatives rejected

- **Accounts on the origin's SQLite:** Cloud Run's disk is ephemeral; the
  Durable Object already is the permanent store.
- **One log with a learner column:** every query would need the filter forever.

## Residual risks

- **No self-service password reset.** The operator uses the singleton account
  store to replace the password hash. Owner-operated account removal clears the
  learner's origin files and Durable Object before removing the account row
  (`docs/deploy.md`).
- **Password strength** is a length of 10–1024 characters. Failed sign-ins
  receive a per-account delay after the fifth attempt.
- **One process for everyone.** A heavy test run slows all learners; one
  shared allowance can be spent by one account.
- **Past test activity stays in the owner's log.** New guest activity is
  isolated.
- **Session trust rests on `SESSION_SECRET` and `PROXY_TOKEN`.** Rotating
  `SESSION_SECRET` signs everyone out, and nothing else.
