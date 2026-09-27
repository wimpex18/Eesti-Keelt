# Learners, guests and profile

The implementation specification for ADR-0006
(`docs/adr/0006-learners-and-guests.md`). The ADR says why; this says what,
file by file. Where this file and the code disagree after implementation,
update this file in the same change.

## Request path

```
owner          ─┐                          scope owner   → DO "singleton"
household      ─┼─► Worker (Access) ──────► scope learner → DO "learner:<id>"
testing / agent ┘   ctx.access identity     scope guest   → no DO
                          │ PROXY_TOKEN + x-eesti-scope + x-eesti-email [+ x-eesti-guest]
                          ▼
   origin: _proxy_guard → identity.resolve → identity.use(scope) → routes
           → config.learner_db(name) → data/*.db | data/learners/<id>/ | data/guest/<sandbox>/
```

| Request reaches the origin with | Scope | Files |
|---|---|---|
| `PROXY_TOKEN`, no `x-eesti-scope` (old Worker, or `OWNER_EMAIL` unset) | `owner` | `config.PROGRESS_DB` … `config.EVENTS_DB` |
| `PROXY_TOKEN`, `x-eesti-scope: owner` | `owner` | owner files |
| `PROXY_TOKEN`, `x-eesti-scope: learner` and `x-eesti-email` | `learner`, id `learner_id(email)` | `config.LEARNERS_DIR/<id>/` |
| `PROXY_TOKEN`, `x-eesti-scope: learner`, no email | refused, 403 | – |
| `PROXY_TOKEN`, `x-eesti-scope: guest` | `guest` | `config.GUEST_DIR/<sandbox>/` |
| guarded origin, wrong or no token | refused, 403 | – |
| unguarded (`cli serve`, tests): header, else `EESTI_SCOPE`, else owner | as chosen | as above |
| any unknown scope value | refused, 403 | – |

`eesti/identity.py` implements this table and `tests/test_identity.py` pins it.

## Origin changes

1. **Middleware** (`eesti/app.py`, `_proxy_guard`): replace the token
   comparison with `identity.resolve(request.headers, request.cookies,
   os.environ)`. None → 403 as today. Run `call_next` inside
   `identity.use(scope)`. For a guest: call `guest.ensure(scope.id)` first; if
   `scope.issued`, set `eesti_guest` on the response (`HttpOnly`, `Secure` when
   the request is https, `SameSite=Lax`, `Max-Age` 86400, `Path=/`). Add
   `x-events-seq` for permanent scopes only, read from that scope's log.
   Starlette runs sync routes in a thread pool and copies the context into it;
   prove that with a test, not by assumption.
2. **Path resolution.** Replace each read of a learner path with
   `config.learner_db("<NAME>")`. The complete list today:
   `eesti/api/deps.py` (5), `eesti/evidence.py` (`connect`, `_open` ×4),
   `eesti/planning.py:189-190`, `eesti/mining.py:86`, `eesti/api/practice.py:452`,
   `eesti/api/state.py` (`_state_paths` and line 312), `eesti/app.py`
   (`_events_seq`). Leave `eesti/recovery.py` and `eesti/cli/*` on the owner's
   attributes (they run outside a request). Re-grep for `_DB` before finishing.
3. **Back channel per learner** (`eesti/api/state.py`): the snapshot, event and
   reminder routes keep requiring `STATE_TOKEN` and now serve the caller's
   permanent scope, because the calling Durable Object sends that learner's
   scope headers. They refuse guest scope (403). `/api/state/import` still
   refuses a store that already has rows, per learner. `/api/content/*` and
   `/api/progress/reset` stay owner-only.
4. **Evidence** (`eesti/evidence.py`): `learner()` returns
   `identity.current().learner` (keep `EESTI_LEARNER` as the owner override for
   the CLI). In `record`, a guest log without the backfill marker gets the
   marker written, never a `NotRestored`; a learner's log behaves like the
   owner's (only its restore may start it). `settle` records `joined` once for a
   `learner` scope whose log has none. Add `profile` to `_register_all`.
5. **Allowances** (`eesti/providers/budget.py`, `breaker.py`): permanent scopes
   bind to the owner's `progress.db` (one household allowance, today's caps);
   guest scope binds to `config.guest_shared_db()` with `GUEST_CAPS` =
   `llm:workers-ai` 100, `tartunlp` 200, `tartunlp-mt` 200, `asr:workers-ai` 50,
   every other lane its normal cap. `/api/engines` reports the caller's
   allowance.
6. **Owner-only actions**, 403 with a Russian `detail` for `learner` and
   `guest`: `/api/notion/push` (the owner's Notion) and every `/api/eval/*`
   route (the owner's voice set). `/api/notion/queue` stays allowed: it writes
   the caller's own store. `/api/reminders/settings` is refused to guests only.
7. **New routes** (`eesti/api/profile.py`, then add it to `eesti.api.ROUTERS`
   before `state.router`): `GET /api/me`, `POST /api/me`, `POST /api/guest/reset`.
   Document them in `docs/architecture.md` (API modules table).
8. **New learner directory.** `config.LEARNERS_DIR/<id>/` is created on the
   first write, like the owner's files; on Cloud Run it is ephemeral and the
   learner's Durable Object restores it.

Everyone sees all material: no `public_only` gating by scope.

## Routes by scope

Every path in `eesti.api.paths()` belongs to exactly one row;
`tests/test_guest_isolation.py::test_every_route_is_classified` holds this
table as data.

| Class | owner | learner | guest | Routes |
|---|---|---|---|---|
| Back channel (404 at the Worker, `STATE_TOKEN` at the origin) | own files | own files | 403 | `/api/events`, `/api/events/import`, `/api/state/export`, `/api/state/import`, `/api/reminders` |
| Back channel, owner only | yes | 403 | 403 | `/api/content/export`, `/api/content/import`, `/api/progress/reset` |
| Answered by the Worker from the caller's object | yes | yes | 403 | `/api/push/key`, `/api/push/subscribe`, `/api/push/unsubscribe` |
| Owner only | yes | 403 | 403 | `/api/notion/push`, `/api/eval/available`, `/api/eval/clip`, `/api/eval/draft/{stem}`, `/api/eval/prompt`, `/api/eval/review/{stem}` |
| Not for guests | yes | yes | 403 | `/api/reminders/settings` |
| Everyone, own store | yes | yes | yes | everything else, including `/api/transcribe`, `/api/me`, `/api/me/export` |
| Guests only | 403 | 403 | yes | `/api/guest/reset` |

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

`deploy/worker.ts`.

1. **Who.** After `requireAccess`, delete caller-sent `x-eesti-scope` and
   `x-eesti-email` (`x-eesti-guest` may pass: it only names a sandbox). Read
   `(await ctx.access?.getIdentity())?.email`. With `OWNER_EMAIL` set: the
   owner's email (case-insensitive) → `owner`; an email in `LEARNER_EMAILS`
   (comma-separated, case-insensitive) → `learner`; anything else → `guest`.
   Set `x-eesti-scope`, and `x-eesti-email` when there is one. Without
   `OWNER_EMAIL`: set neither, as today. `learnerId(email)` in TypeScript is
   SHA-256 via `crypto.subtle`, `l-` plus the first 16 hex digits, identical to
   `identity.learner_id` (a test pins one vector in both).
2. **Which object.** `stub(env)` becomes `stubFor(env, who)`: `singleton` for the
   owner, `learner:<id>` for a learner, none for a guest. The object remembers
   its `who` (scope and email) in storage on `ensureRestored(who)`, and
   `headers()` adds `x-eesti-scope`/`x-eesti-email` from it to every back-channel
   call, so restore, snapshots, event pulls and reminders touch that learner's
   files only. `syncCorpus` runs in `singleton` only.
3. **Guests.** No object: skip `ensureRestored`, `snapshot` and `pullEvents`;
   `/api/push/*` → 403 with a Russian message.
4. **Speech.** `transcribe` forwards the caller's scope headers to
   `/api/transcribe/text`, and pulls events into the caller's object.
5. **Cron.** `scheduled` calls `remind()` on `singleton` and on
   `learner:<id>` for each address in `LEARNER_EMAILS`.
6. **`BACK_CHANNEL`** is unchanged: those paths stay 404 from outside.

Local check: `wrangler dev` with `access.dev.identity.email` set to the owner,
then to a `LEARNER_EMAILS` address, then to another address (`docs/deploy.md`).

### Deploy and operator steps

- New Worker secrets `OWNER_EMAIL` and `LEARNER_EMAILS`.
  `.github/workflows/deploy.yml` pushes them like the others and warns (does not
  fail) when `OWNER_EMAIL` is missing; an empty `LEARNER_EMAILS` is valid.
- Adding a learner, in `docs/deploy.md` with no values: add the email to the
  Worker's Access policy and to `LEARNER_EMAILS`, redeploy; the person signs in
  with the one-time PIN Access sends and sets their name on Profiil.
- Adding a testing account: the Access policy only. For headless agents,
  optionally a service token with a *Service Auth* policy, its id and secret in
  the agent's environment.
- Removing a learner and erasing their data: the operator procedure in
  `docs/deploy.md`, applied to that learner's object and directory.
- Nothing changes on Cloud Run.

## Profile

`GET /api/me` returns the shape documented in `eesti/profile.py` `summary`.
Sources, all existing:

| Field | From |
|---|---|
| `name` | newest `profile-set` event in the scope's log |
| `email` | `identity.current().email` (the Worker, from Access; null for a service token) |
| `since` | the `joined` event (registration), else the first event other than `backfill` (a `legacy-row` counts: it is real history) |
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
  - *Konto* (аккаунт): *Põhikonto* (основной, прогресс сохраняется),
    *Õppija* (ученик, свой прогресс сохраняется) or *Külaline* (гость,
    песочница), so everyone sees at once which account is signed in.
  - *Õpib alates* (учится с: registration) and *Viimati* (последнее занятие): dates in
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
- `tests/test_guest_isolation.py`, `tests/test_learners.py`,
  `tests/test_profile.py` — skeletons naming every requirement above; remove
  their skips and fill them in.
- Beside the `BACK_CHANNEL` check in `tests/test_origin_guard.py`: the Worker
  strips caller-sent `x-eesti-scope` and `x-eesti-email`, picks the object by
  scope, refuses `/api/push/*` to a guest, and its `learnerId` matches
  `identity.learner_id` on a fixed vector (read from `deploy/worker.ts`, as
  that test does).
- Browser journeys (`tests/test_e2e_journeys.py`): the profile tab in all four
  pairings, renaming, the guest line and sandbox reset; journeys that write
  progress run in a guest sandbox by default.
