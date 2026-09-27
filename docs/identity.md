# Owner, guest and profile

The implementation specification for ADR-0006
(`docs/adr/0006-owner-and-guest.md`). The ADR says why; this says what, file
by file. Where this file and the code disagree after implementation, update
this file in the same change.

## Request path

```
owner account     ─┐                         x-eesti-scope: owner, x-eesti-email
testing account   ─┼─► eesti-keelt Worker ──► + PROXY_TOKEN ──► Cloud Run origin
agent (token)     ─┘   (Cloudflare Access)   x-eesti-scope: guest, x-eesti-guest
                                                     │
              _proxy_guard → identity.resolve → identity.use(scope) → routes
                        → config.learner_db(name) → owner files or sandbox files
```

| Request reaches the origin with | Scope | Stores |
|---|---|---|
| `PROXY_TOKEN`, no `x-eesti-scope` (old Worker, or `OWNER_EMAIL` unset) | `owner` | `config.PROGRESS_DB` … `config.EVENTS_DB` |
| `PROXY_TOKEN`, `x-eesti-scope: owner` | `owner` | owner files |
| `PROXY_TOKEN`, `x-eesti-scope: guest` | `guest` | `config.GUEST_DIR/<sandbox>/` |
| guarded origin, wrong or no token | refused, 403 | – |
| unguarded (`cli serve`, tests): header, else `EESTI_SCOPE`, else owner | as chosen | as above |
| any unknown scope value | refused, 403 | – |

`eesti/identity.py` implements this table and `tests/test_identity.py` pins it.

## Origin changes

1. **Middleware** (`eesti/app.py`, `_proxy_guard`): replace the token
   comparison with `identity.resolve(request.headers, request.cookies,
   os.environ)`. None → 403 as today. Run `call_next` inside
   `identity.use(scope)`. For a guest: call `guest.ensure(sandbox)` first; if
   `scope.issued`, set `eesti_guest` on the response (`HttpOnly`, `Secure` when
   the request is https, `SameSite=Lax`, `Max-Age` 86400, `Path=/`); do **not**
   add `x-events-seq`. Starlette runs sync routes in a thread pool and copies
   the context into it; prove that with a test, not by assumption.
2. **Path resolution.** Replace each read of a learner path with
   `config.learner_db("<NAME>")`. The complete list today:
   `eesti/api/deps.py` (5), `eesti/evidence.py` (`connect`, `_open` ×4),
   `eesti/planning.py:189-190`, `eesti/mining.py:86`, `eesti/api/practice.py:452`,
   `eesti/api/state.py:312`. Leave these on the owner's attributes:
   `eesti/app.py` `_events_seq` (skip it for guests), `eesti/api/state.py`
   `_state_paths` and the event export/import (the snapshot is the owner's),
   `eesti/recovery.py`, `eesti/cli/*`. Re-grep for `_DB` before finishing.
3. **Evidence** (`eesti/evidence.py`): `learner()` returns
   `identity.current().learner` (keep `EESTI_LEARNER` as the owner override for
   the CLI). In `record`, a guest log without the backfill marker gets the marker
   written, never a `NotRestored`. Add `profile` to `_register_all`.
4. **Allowances** (`eesti/providers/budget.py`): for a guest scope, count in
   `config.guest_shared_db()` against `GUEST_CAPS` = `llm:workers-ai` 100,
   `tartunlp` 200, `tartunlp-mt` 200, `asr:workers-ai` 50, every other lane
   its owner cap. The breaker stays per store. `/api/engines` reports the
   caller's own allowance.
5. **Refusals** for a guest, 403 with a Russian `detail`: `/api/notion/push`
   (the `Vead` log is the owner's) and every `/api/eval/*` route (the owner's
   private speech set). Queueing a correction (`/api/notion/queue`) is allowed:
   it stays in the sandbox.
6. **New routes** (`eesti/api/profile.py`, then add it to `eesti.api.ROUTERS`
   before `state.router`): `GET /api/me`, `POST /api/me`, `POST /api/guest/reset`.
   Document them in `docs/architecture.md` (API modules table).

Guests see all material: no `public_only` gating by scope (ADR-0006, 6).

## Routes for a guest

Every path in `eesti.api.paths()` belongs to exactly one row;
`tests/test_guest_isolation.py::test_every_route_is_classified_for_a_guest`
holds this table as data.

| Class | Routes |
|---|---|
| Back channel (404 at the Worker, `STATE_TOKEN` at the origin; owner files only) | `/api/events`, `/api/events/import`, `/api/state/export`, `/api/state/import`, `/api/content/export`, `/api/content/import`, `/api/progress/reset`, `/api/reminders` |
| Answered by the Worker, refused to a guest | `/api/push/key`, `/api/push/subscribe`, `/api/push/unsubscribe` |
| Refused to a guest by the origin | `/api/notion/push`, `/api/eval/available`, `/api/eval/clip`, `/api/eval/draft/{stem}`, `/api/eval/prompt`, `/api/eval/review/{stem}`, `/api/reminders/settings` |
| Allowed, sandboxed | everything else, including `/api/transcribe`, `/api/me`, `/api/me/export`, `/api/guest/reset` |

## Guest sandboxes

`eesti/guest.py`. A sandbox is `GUEST_DIR/<name>/` with the five learner files
and a `last-used` file whose mtime is the idle clock. `ensure` makes it and
writes the log's `backfill` marker; `sweep` (at most once a minute) drops
sandboxes idle over 24 h, then the oldest beyond 50; `reset` removes one.
`shared.db` holds the guest allowances and is never swept. Names come only from
`identity.sandbox_name`, so a name is always a safe single directory.

Agents and tests choose a sandbox with `x-eesti-guest: <name>` (Playwright:
`extraHTTPHeaders`); a browser without it gets a cookie. Start a run with
`POST /api/guest/reset` for a clean slate.

## Worker changes

`deploy/worker.ts`, `fetch`, after `requireAccess`:

1. Delete `x-eesti-scope` and `x-eesti-email` from the incoming headers
   (`x-eesti-guest` may pass: it only names a sandbox).
2. `const who = (await ctx.access?.getIdentity())?.email`. With `OWNER_EMAIL`
   set: scope `owner` when `who` equals it case-insensitively, otherwise
   `guest`; set both headers (`x-eesti-email` only when `who` exists). Without
   `OWNER_EMAIL`: set neither, as today.
3. For a guest: `/api/push/*` → 403 with a Russian message; skip
   `learner.snapshot()` and `learner.pullEvents()` (the origin sends no
   `x-events-seq` anyway). Restore gating stays as is: a guest waiting for the
   owner's restore on a cold start is harmless.
4. The speech path (`transcribe`) forwards the same scope headers to
   `/api/transcribe/text`, so a guest transcript lands in the sandbox.

Local check: `wrangler dev` with `access.dev.identity.email` set to the owner,
then to another address (`docs/deploy.md`).

### Deploy and operator steps

- New Worker secret `OWNER_EMAIL`. `.github/workflows/deploy.yml` pushes it
  like the others and warns (does not fail) when it is missing.
- The owner, once, in the Cloudflare dashboard: add the testing account's email
  to the Worker's Access policy; optionally create a service token and a
  *Service Auth* policy for headless agents, and put its id and secret in the
  agent's environment. Write these steps into `docs/deploy.md` with no values.
- Nothing changes on Cloud Run.

## Profile

`GET /api/me` returns the shape documented in `eesti/profile.py` `summary`.
Sources, all existing:

| Field | From |
|---|---|
| `name` | newest `profile-set` event in the scope's log |
| `email` | `identity.current().email` (the Worker, from Access; null for a service token) |
| `since` | the first event in the log other than `backfill` (a `legacy-row` counts: it is real history) |
| `last_active`, `active_days_28`, `rhythm` | `learner.daily_activity` and `learner.PRACTICE_EVENTS` |
| `level.current` | the level of `progress.resume`'s topic |
| `level.goal` | `exam.goal(progress)` |
| `level.checkpoints` | `checkpoint.passed_levels` |
| `milestones` | `milestones.for_level` for each of `config.LEVELS` |
| `totals` | `attempts` rows, `progress.mastered`, generator topics, review cards, `vocab` known |

`POST /api/me {"name": …}` records `profile-set` (`profile.clean_name`: trimmed,
1–60 characters, blank clears). No other field is editable: email belongs to
Access, dates and levels to the evidence.

## Profile page

Content, so plain page and the shared treatment (`DESIGN.md` "Adding a page or
section", "Layout rhythm"); no glass, no new card, shadow, colour or streak.
Starting point: `docs/skeletons/profile.js`.

- **Where.** A third tab in the Eksam mode, after Edenemine:
  `<button role="tab" data-tab="profile">`, icon `◉`-style glyph like its
  neighbours, label `Profiil`. Panel `section.panel#tab-profile`; `router.js`
  loads it on open; `docs/app-structure.md` lists it (the doc test checks).
- **Head.** `page-title` *Profiil* with the gloss *профиль*, and a one-line
  Russian lede saying the page shows who is learning and what the evidence says.
- **Rows** (hairline rows, label left in Estonian with its Russian gloss, value
  right; stacked on the phone):
  - *Nimi* (имя): the value, and *Muuda* (изменить) opening an inline field
    with *Salvesta* (сохранить) and *Loobu* (отмена); errors are the server's
    Russian `detail`.
  - *E-post* (эл. почта): the Access email; for a service token, *puudub*
    (нет).
  - *Režiim* (режим): *Põhikonto* (основной аккаунт, прогресс сохраняется) or
    *Külaline* (гость, песочница), so the owner always sees which account is
    signed in.
  - *Õpib alates* (учится с) and *Viimati* (последнее занятие): dates in
    Russian format; empty log → *Veel mitte* (пока нет).
  - *Tase* (уровень): current path level, exam goal (level and date, or a link
    to Ülevaade to choose one), checkpoints passed.
- **Märgid** (значки): a level switch (`role="tablist"`, A1 · A2 · B1, the
  current level selected) over `sealsHtml(milestones[level])`.
- **Rütm** (ритм): `rhythmHtml(rhythm)` and *active days in the last four
  weeks*, exactly as Edenemine words it.
- **Kokku** (итого): attempts, topics mastered of total, review cards, known
  words, each as a number with a Russian label (`ruCount`).
- **Guest.** A line at the top of every screen (not glass, not dismissible):
  *Külaline* and, in Russian, that this is a sandbox and progress will not be
  kept. On the profile, *Tühjenda liivakast* (очистить песочницу) calls
  `POST /api/guest/reset`, then reloads the profile.
- **Viewports.** Phone 402×874 and 874×402 (touch), iPad mini 744×1133, desktop
  1440×900, light and dark: no horizontal scroll, the name field and buttons at
  least 44px, the rail's own cards unchanged (the profile adds none).

## Tests to add

- `tests/test_identity.py` (done) — scope resolution and paths.
- `tests/test_guest_isolation.py`, `tests/test_profile.py` — skeletons naming
  every requirement above; remove their skips and fill them in.
- Beside the `BACK_CHANNEL` check in `tests/test_origin_guard.py`: the Worker
  strips caller-sent `x-eesti-scope` and `x-eesti-email`, and refuses
  `/api/push/*` to a guest (read from `deploy/worker.ts`, as that test does).
- Browser journeys (`tests/test_e2e_journeys.py`): the profile tab in all four
  pairings, renaming, the guest line and sandbox reset; journeys that write
  progress run in a guest sandbox by default.
