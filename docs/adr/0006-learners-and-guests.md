# ADR-0006: Learners and guests

**Status:** Accepted, implementation in progress (`docs/identity.md`).
**Scope:** a household of up to two permanent learners with in-app accounts,
throwaway guests for tests and agents, one origin, the existing Cloudflare
Access door unchanged. Supersedes ADR-0005's deferral of per-identity Durable
Objects: there is now a real second learner.

## Problem

The app has one evidence log. Real study, exploratory clicks and Claude/Codex
runs all write into it and count as mastery, FSRS cards and readiness. A second
person in the household has nowhere of her own to study.

## Decision

Accounts live in the app. Access stays exactly as configured today: it is the
door to the whole app, not the account system.

| Scope | Who | How | Origin files | Durable Object | Lifetime |
|---|---|---|---|---|---|
| `owner` | the first account created | signed in | `data/*.db` (today's paths) | `singleton` (today's) | permanent |
| `learner` | the second account | signed in | `data/learners/<id>/*.db` | `learner:<id>` | permanent |
| `guest` | Claude, Codex, tests, anyone not signed in | no session | `data/guest/<sandbox>/*.db` | none | throwaway: cold start, reset, 24 h idle |

1. **Sign-up and sign-in in the app, owned by the Worker.** Accounts (id,
   email, password hash, created) live in the `singleton` Durable Object's SQL
   store, so they are permanent and never on Cloud Run's ephemeral disk. The
   Worker answers `/api/auth/*` itself, as it does `/api/push/*`. Passwords are
   PBKDF2-SHA-256 (WebCrypto, 100 000 iterations, per-account salt). The session
   is an `HttpOnly`, `Secure`, `SameSite=Lax` cookie holding the account id and
   expiry, signed with HMAC by the Worker secret `SESSION_SECRET`; 90 days.
2. **The first account is the owner.** It inherits everything recorded before
   accounts existed. Every later account is a `learner` with an id `l-` + 16 hex
   digits. Sign-up closes at `MAX_ACCOUNTS` (default 2), so a stray agent cannot
   create a third account.
3. **Not signed in is a guest.** The full app, all material, in a sandbox named
   by `x-eesti-guest` (agents and tests pick one) or the `eesti_guest` cookie. At
   most 50 sandboxes, dropped after 24 h idle.
4. **The Worker tells the origin who it is.** It deletes caller-sent
   `x-eesti-scope`, `x-eesti-learner` and `x-eesti-email`, then sets them from
   the session. The origin trusts them only with `PROXY_TOKEN`. No scope header
   means owner, so an older Worker behaves as today (`eesti/identity.py`).
5. **One process, request-scoped paths** via `config.learner_db(name)`. The
   owner's paths are unchanged; no new service, engine or framework.
6. **One Durable Object per permanent learner**, the existing `LearnerState`
   class named per learner, holding that learner's log, snapshot and push
   subscriptions and restoring them independently. Back-channel calls carry the
   learner's scope headers. The corpus stays in `singleton`. Guests have none:
   no `x-events-seq`, back channel refused, own backfill marker.
7. **Everyone sees all material.** Everyone is already behind Access.
8. **Owner only:** the Notion `Vead` push and the private speech eval set.
   Reminders for both permanent learners; none for guests.
9. **One household allowance** for provider calls (the owner's `progress.db`);
   guests count in `data/guest/shared.db` with smaller `GUEST_CAPS`.
10. **Profile from the log.** Name (`profile-set`, asked at sign-up, editable),
    email (from the account), registration (`joined`), activity, level,
    milestones and rhythm. No streak.

## Contracts to preserve

- Until the first account exists, and without `SESSION_SECRET`, every request is
  the owner, exactly as today.
- The owner's paths, `singleton` object, event ids and snapshots are unchanged.
- Event `learner`: `owner`, `l-<hex>`, or `guest:<sandbox>`. `profile-set` and
  `joined` have no-op applies so strict replay accepts them.
- ADR-0005 route contracts, signed item refs and offline queue IDs.

## Alternatives rejected

- **Access as the account system** (emails in a policy): needs each person's
  email configured in Cloudflare; the owner wants sign-up in the app.
- **Accounts on the origin's SQLite:** Cloud Run's disk is ephemeral; the Durable
  Object already is the permanent store.
- **One log with a learner column:** every query would need the filter forever.

## Residual risks

- **No password reset.** There is no mail service. A forgotten password needs
  the operator (`docs/deploy.md`: delete the account row in the Durable Object;
  the learner's progress stays under their id only if the id is kept). Accepted
  for two people who live together.
- **Order matters once.** Whoever signs up first becomes the owner and inherits
  the existing progress: the owner must sign up before anyone else.
- **Sign-up is open to anyone past Access until `MAX_ACCOUNTS`.** Agents are
  told not to sign up; the cap bounds the damage.
- **Password strength** is only a minimum length (10). No rate limiting beyond a
  per-account failure delay in the Durable Object.
- **One process for everyone.** A heavy test run slows both learners; the
  household allowance can be spent by one person.
- **Past test activity stays in the owner's log.** This stops new pollution.
- **Session trust rests on `SESSION_SECRET` and `PROXY_TOKEN`.** Rotating
  `SESSION_SECRET` signs everyone out, and nothing else.
