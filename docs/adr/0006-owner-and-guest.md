# ADR-0006: Owner and guest

**Status:** Accepted, implementation in progress (`docs/identity.md`).
**Scope:** one owner, any number of throwaway guests, one origin.

## Problem

The app has one evidence log. The owner's real study, the owner's own
exploratory clicks, Claude/Codex browser runs and journey tests all write into
it, and replay turns every one of those events into mastery, FSRS cards and
readiness. Nothing can tell them apart afterwards.

## Decision

Two scopes, decided by the front door, never by the page:

| Scope | Who | Reached through | Stores | Lifetime |
|---|---|---|---|---|
| `owner` | the owner, signed in | `eesti-keelt` Worker, Cloudflare Access | `data/*.db` (today's files) | permanent: Durable Object log and snapshots |
| `guest` | AI agents, tests, the owner trying things | `eesti-keelt-guest` Worker, no Access | `data/guest/<sandbox>/*.db` | the container's disk: gone on a cold start, on reset, or after 24 h idle |

1. **A second Worker is the guest front door.** `deploy/guest.ts`, deployed as
   the `guest` environment in `wrangler.jsonc` (`eesti-keelt-guest.wimpex18.workers.dev`),
   with no Access, no Durable Object, no cron, no AI binding and no home speech
   service. A separate hostname means the page, its absolute `/api/...` paths,
   the service worker and IndexedDB work unchanged and are isolated by the
   browser's own origin rules. A path prefix under the Access-protected host was
   rejected: every absolute URL in the page would need rewriting.
2. **The origin derives the scope from which secret the Worker presents.** The
   owner Worker keeps `PROXY_TOKEN`; the guest Worker holds only
   `GUEST_PROXY_TOKEN`. The origin maps token to scope (`eesti/identity.py`).
   No client header can choose a scope on the deployment. Without `PROXY_TOKEN`
   (local `cli serve`, tests) the guard is off and `x-eesti-scope` or
   `EESTI_SCOPE` chooses, default `owner`.
3. **One process, request-scoped paths.** Learner database paths are resolved
   per request through `config.learner_db(name)`, which reads the request's
   scope from a context variable. `config.PROGRESS_DB` and friends stay the
   owner paths, so the CLI, the snapshot routes and the existing tests are
   unchanged. No second service, database engine or framework.
4. **Guest sandboxes are per caller.** A guest request names its sandbox with the
   `eesti_guest` cookie (set on first contact) or the `x-eesti-guest` header
   (agents and tests choose a readable name). Two agents running at once do not
   see each other's progress. At most 50 sandboxes; the oldest idle one is
   dropped first; any idle for 24 h is dropped.
5. **Guest writes never reach the owner's permanence.** For guest requests the
   origin omits `x-events-seq`, the guest Worker has no Durable Object to copy
   into, and every `STATE_TOKEN` route stays unreachable (the guest Worker holds
   no `STATE_TOKEN`). A guest log starts with its own backfill marker, so the
   restore gate (`NotRestored`) never applies to it.
6. **Guests on the public host get only redistributable material.** Guest scope
   reached through `GUEST_PROXY_TOKEN` sets `public = True`, and every content
   query passes `public_only=True` (the filter `eesti/library.py` and
   `eesti/sources.py` already implement). Routes whose whole purpose is
   owner-only material (HARNO files, EKI recordings, ERR audio) answer 403 with
   a Russian reason. Local guest scope is not public: the owner's machine may
   show everything.
7. **Guests have their own, smaller allowances.** Provider budget and breaker
   for guest scope count in `data/guest/shared.db`, one store for all
   sandboxes, with `budget.GUEST_CAPS`. When spent, the existing degraded
   (deterministic) path answers. Guests never send to Notion and never
   subscribe to reminders.
8. **The profile is derived from the log, not a new store.** `GET /api/me`
   reports name, email, first and last activity, level, milestones and rhythm;
   `POST /api/me` records a `profile-set` event (the name). Email comes from the
   Access identity (`ctx.access.getIdentity()`), passed by the owner Worker as
   `x-eesti-email` and trusted only with `PROXY_TOKEN`. The app has no streak
   and adds none: *Rütm* is the rhythm (`DESIGN.md`: nothing resets).

## Contracts to preserve

- Owner behaviour is unchanged when the guest Worker is not deployed and when
  a request carries the old headers: an owner request without any new header is
  still owner.
- Event envelopes keep `learner`; owner events stay `owner`, guest events are
  `guest:<sandbox>`. `profile-set` is registered with a no-op apply so strict
  replay (`cli verify-backup`) accepts it.
- Stable route contracts, signed item refs and offline queue IDs from ADR-0005.
- No new persistence source: the profile name lives in the log.

## Alternatives rejected

- **Access service tokens for agents.** Keeps licensed material private, but a
  browser agent cannot add `CF-Access-Client-*` headers, and the owner asked for
  an unauthenticated path.
- **Per-identity Durable Objects** (ADR-0005, still deferred). The origin is the
  single writer; naming more objects would not isolate its SQLite files.
- **A second Cloud Run service for guests.** Doubles cold starts and the build,
  and the free tier's one-instance rule, for isolation a directory gives.
- **Marking guest events inside the owner log and filtering on replay.** Every
  projection, readiness and planner query would need the filter forever; one
  missed query leaks test data into mastery.

## Residual risks

- **The guest host is public.** Anyone with the URL can use it. Material is
  gated to redistributable sources and hosted lanes are capped, but a caller
  can still spend the guest allowance daily and wake Cloud Run. Accepted for a
  personal app; if abused, put the guest Worker behind an Access service-token
  policy and give agents the token through their environment, not chat.
- **Guest counters reset on a cold start**, so the guest allowance is a per-boot
  ceiling, not a strict daily one.
- **Guest and owner share one origin process.** A guest flood slows the owner;
  there is no per-scope rate limit beyond the allowances.
- **Guest runs see less material** than the owner (no ERR, Selges keeles or
  HARNO files on the public host). A journey that needs owner-only content must
  run locally in guest scope.
- **Owner's past test activity stays in the log.** This change stops new
  pollution; it does not clean history. Cleaning is a separate, owner-approved
  operation (export, filter, `cli verify-backup`, restore) and is not built here.
- **Email trust rests on the Worker.** The origin accepts `x-eesti-email` only
  with `PROXY_TOKEN`; a leaked `PROXY_TOKEN` already grants owner access.
