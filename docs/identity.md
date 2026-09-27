# Owner, guest and profile

The implementation specification for ADR-0006
(`docs/adr/0006-owner-and-guest.md`). The ADR says why; this says what, file
by file. Where this file and the code disagree after implementation, update
this file in the same change.

## Request path

```
owner:  browser ─► eesti-keelt (Access) ── PROXY_TOKEN + x-eesti-email ──┐
guest:  agent   ─► eesti-keelt-guest ───── GUEST_PROXY_TOKEN ────────────┤
                                                                         ▼
          Cloud Run origin: _proxy_guard → identity.resolve → identity.use(scope)
                            → routes → config.learner_db(name) → owner or sandbox files
```

| Front door | Origin sees | Scope | `public` | Stores |
|---|---|---|---|---|
| `deploy/worker.ts` | `PROXY_TOKEN` | `owner` | no | `config.PROGRESS_DB` … `config.EVENTS_DB` |
| `deploy/guest.ts` | `GUEST_PROXY_TOKEN` | `guest` | yes | `config.GUEST_DIR/<sandbox>/` |
| none (`cli serve`, tests), no header | – | `owner` (or `EESTI_SCOPE`) | no | owner files |
| none, `x-eesti-scope: guest` | – | `guest` | only if `EESTI_GUEST_PUBLIC=1` | sandbox |
| guarded origin, any other token | – | refused, 403 | – | – |

`eesti/identity.py` implements this table and `tests/test_identity.py` pins it.

## Origin changes

1. **Middleware** (`eesti/app.py`, `_proxy_guard`): replace the single token
   comparison with `identity.resolve(request.headers, request.cookies,
   os.environ)`. None → 403 as today. Run `call_next` inside
   `identity.use(scope)`. For a guest: call `guest.ensure(sandbox)` first; if
   `scope.issued`, set `eesti_guest` on the response (`HttpOnly`, `Secure` when
   the request is https, `SameSite=Lax`, `Max-Age` 86400, `Path=/`); do **not**
   add `x-events-seq`. Starlette runs sync routes in a thread pool; the context
   variable is copied into it, which is the behaviour needed. Verify with a test,
   not by assumption.
2. **Path resolution.** Replace each read of a learner path with
   `config.learner_db("<NAME>")`. The complete list today:
   `eesti/api/deps.py` (5), `eesti/evidence.py` (`connect`, `_open` ×4),
   `eesti/planning.py:189-190`, `eesti/mining.py:86`, `eesti/api/practice.py:452`,
   `eesti/api/state.py:312`, `eesti/app.py` (`_events_seq`: owner only, keep
   `config.EVENTS_DB` and skip it for guests). Leave these on the owner's
   attributes: `eesti/api/state.py` `_state_paths` (the snapshot is the owner's),
   `eesti/recovery.py`, `eesti/cli/*`. Re-grep for `_DB` before finishing.
3. **Evidence** (`eesti/evidence.py`): `learner()` returns
   `identity.current().learner` (keep `EESTI_LEARNER` as the owner override for
   the CLI). In `record`, a guest log without the backfill marker gets the marker
   written, never a `NotRestored`. Add `profile` to `_register_all`.
4. **Allowances** (`eesti/providers/budget.py`, `breaker.py`): for a guest
   scope, count in `config.guest_shared_db()` with `GUEST_CAPS`:
   `llm:workers-ai` 30, `tartunlp` 100, `tartunlp-mt` 100, `asr:workers-ai` 0,
   every other lane 0. The breaker may stay per store. `/api/engines` reports
   the caller's own allowance.
5. **Licence gate.** Where a route calls a content function that takes
   `public_only`, pass `identity.current().public`. `public_only` never becomes a
   query parameter.
6. **Refusals** for guests, with a Russian `detail`:
   `/api/notion/push` (nothing leaves the app from a sandbox) and
   `/api/eval/*` (the owner's private speech set), always; the owner-only file
   routes below, when `public`.
7. **New routes** (`eesti/api/profile.py`, then add it to `eesti.api.ROUTERS`
   before `state.router`): `GET /api/me`, `POST /api/me`, `POST /api/guest/reset`.
   Document them in `docs/architecture.md` (API modules table).

## Routes for a public guest

Every path in `eesti.api.paths()` belongs to exactly one row;
`tests/test_guest_isolation.py::test_every_route_is_classified_for_a_public_guest`
holds this table as data.

| Class | Routes |
|---|---|
| Back channel (404 at both Workers, `STATE_TOKEN` at the origin) | `/api/events`, `/api/events/import`, `/api/state/export`, `/api/state/import`, `/api/content/export`, `/api/content/import`, `/api/progress/reset`, `/api/reminders` |
| Answered by the Worker | `/api/push/*` (guest: 404), `/api/asr/home` (guest: not configured), `/api/transcribe` (guest: degraded, no engine) |
| Refused to every guest | `/api/notion/push`, `/api/eval/available`, `/api/eval/clip`, `/api/eval/draft/{stem}`, `/api/eval/prompt`, `/api/eval/review/{stem}`, `/api/reminders/settings` |
| Refused when public (owner-only files) | `/api/exam/file/{item_id}`, `/api/exam/image/…`, `/api/exam/page/…`, `/api/exam/pages/{item_id}`, `/api/exam/text/{item_id}`, `/api/exam/native/{item_id}`, `/api/exam/native/{item_id}/check`, `/api/pronounce` (EKI recordings, `licences.AUDIO` is not redistributable) |
| Content-gated when public (`public_only`) | `/api/library`, `/api/library/{item_id}` (404 for an owner-only item), `/api/modes`, `/api/reading/next`, `/api/read/questions/{item_id}`, `/api/read/answer`, `/api/lesson/{topic}` (linked texts), `/api/plan` (text block), `/api/exam/{level}` (catalogue rows) |
| Allowed, sandboxed | everything else: practice, review, vocab, grammar, dictation, speaking, mock, checkpoint, goal, status, readiness, milestones, `/api/me`, `/api/me/export`, `/api/guest/reset`, health, sources |

Confirm each gated route really reaches owner-only rows before gating it, and
each allowed route really cannot; this table is the starting classification,
not a proof.

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

## Guest Worker

`deploy/guest.ts`, `wrangler.jsonc` → `env.guest`. It strips `x-proxy-token`,
`x-state-token`, `x-eesti-scope` and `x-eesti-email` from the caller, sets
`GUEST_PROXY_TOKEN`, 404s the back channel and `/api/push/*`, answers
`/api/transcribe` degraded and `/api/asr/home` as not configured, and forwards
everything else. `wrangler deploy --env guest --dry-run` must list no bindings.

The owner Worker (`deploy/worker.ts`) changes in two places: strip
`x-eesti-scope`, `x-eesti-guest` and `x-eesti-email` from the incoming request,
then set `x-eesti-email` from `(await ctx.access?.getIdentity())?.email` when
present. Everything about restore, snapshots and events is unchanged.

### Deploy

- `.github/workflows/deploy.yml`: after the owner deploy, push
  `CLOUD_RUN_URL` and `GUEST_PROXY_TOKEN` with `wrangler secret put --env guest`
  and run `wrangler deploy --env guest`. Pass `--env=""` to the owner deploy.
  Skip the guest steps with a warning when `GUEST_PROXY_TOKEN` is not set, so
  the owner deploy never depends on it.
- Cloud Run needs `GUEST_PROXY_TOKEN` as a secret env var beside `PROXY_TOKEN`
  (`deploy/setup.sh` or the operator note in `docs/deploy.md`). Until it is set,
  the origin refuses the guest Worker (403), which is the safe failure.
- Operator steps the owner does once, in Google Cloud Shell: generate the token,
  add it to Cloud Run and to the repository secrets. Write them into
  `docs/deploy.md`; never print the value.
- The guest host must **not** get Cloudflare Access. `deploy/guest.ts` does not
  call `requireAccess`.

## Profile

`GET /api/me` returns the shape documented in `eesti/profile.py` `summary`.
Sources, all existing:

| Field | From |
|---|---|
| `name` | newest `profile-set` event in the scope's log |
| `email` | `identity.current().email` (owner Worker → Access) |
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
  - *E-post* (эл. почта): the Access email, or for a guest *Külaline* with the
    Russian note that a guest has no account.
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
- Beside the `BACK_CHANNEL` check in `tests/test_origin_guard.py`: `deploy/guest.ts`
  `REFUSED` equals `deploy/worker.ts` `BACK_CHANNEL`.
- Browser journeys (`tests/test_e2e_journeys.py`): the profile tab in all four
  pairings, renaming, the guest line and sandbox reset; journeys that write
  progress run in a guest sandbox by default.
