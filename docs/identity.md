# Learners, guests and profile

This document describes the implemented identity and profile boundaries from
ADR-0006 (`docs/adr/0006-learners-and-guests.md`).

## Request path

```
browser / agent ─► Worker (public entry)
                   ├─ /api/auth/*  sign-up, sign-in, sign-out, me  (accounts in DO "singleton")
                   └─ session cookie → owner | learner <id> | no session → guest
                        │ PROXY_TOKEN + x-eesti-scope [+ x-eesti-learner, x-eesti-email, x-eesti-guest]
                        ▼
   origin: IdentityMiddleware → identity.resolve → identity.use(scope) → routes
           → config.learner_db(name) → data/*.db | data/learners/<id>/ | data/guest/<sandbox>/
```

| Request reaches the origin with | Scope | Files |
|---|---|---|
| `PROXY_TOKEN`, no `x-eesti-scope` (trusted operator compatibility) | `owner` | `config.PROGRESS_DB` … `config.EVENTS_DB` |
| `PROXY_TOKEN`, `x-eesti-scope: owner` | `owner` | owner files |
| `PROXY_TOKEN`, `x-eesti-scope: learner`, valid `x-eesti-learner` | `learner` | `config.LEARNERS_DIR/<id>/` |
| `PROXY_TOKEN`, `x-eesti-scope: learner`, missing or malformed id | refused, 403 | – |
| `PROXY_TOKEN`, `x-eesti-scope: guest` | `guest` | `config.GUEST_DIR/<sandbox>/` |
| guarded origin, wrong or no token | refused, 403 | – |
| unguarded (`cli serve`, tests): header, else `EESTI_SCOPE`, else owner | as chosen | as above |
| any unknown scope value | refused, 403 | – |

`eesti/identity.py` implements this table and `tests/test_identity.py` pins it.

## Origin

1. **Middleware** (`eesti/app.py`, `IdentityMiddleware`) resolves the request
   headers, cookies and environment through `identity.resolve`; a refused
   identity returns 403. `call_next` runs inside `identity.use(scope)`. For a
   guest it ensures the sandbox first and, when the sandbox is newly issued,
   sets `eesti_guest` (`HttpOnly`, `Secure` on HTTPS, `SameSite=Lax`,
   `Max-Age` 86400, `Path=/`). Permanent scopes receive `x-events-seq` from
   their own log.
   A pure ASGI middleware keeps the context through sync route execution;
   the guest and learner isolation tests prove that the thread-pool routes use it.
2. **Path resolution.** Request code resolves learner state through
   `config.learner_db("<NAME>")`. Recovery and CLI commands use the owner's
   paths because they run outside a request.
3. **Back channel per learner** (`eesti/api/state.py`): the snapshot, event and
   reminder routes require `STATE_TOKEN` and serve the caller's
   permanent scope, because the calling Durable Object sends that learner's
   scope headers. They refuse guest scope (403). `/api/state/import` still
   refuses a store that already has rows, per learner. `/api/content/*` and
   `/api/progress/reset` stay owner-only.
4. **Evidence** (`eesti/evidence.py`): `learner()` returns
   `identity.current().learner`; `EESTI_LEARNER` remains the owner override for
   the CLI. In `record`, a guest log without the backfill marker gets the
   marker written, never a `NotRestored`; a learner's log behaves like the
   owner's (only its restore may start it). `settle` records `joined` once for a
   `learner` scope whose log has none. `_register_all` includes `profile`.
5. **Allowances** (`eesti/providers/budget.py`, `breaker.py`): permanent scopes
   bind to the owner's `progress.db` (one household allowance, today's caps);
   guest scope counts in the same store under `guest:` lane names, so the
   owner's snapshot carries it across cold starts, with `GUEST_CAPS` =
   `llm:workers-ai` 100, `tartunlp` 200, `tartunlp-mt` 200, `asr:workers-ai` 50,
   every other lane its normal cap. `/api/engines` reports the caller's
   allowance.
6. **Owner-only actions**, 403 with a Russian `detail` for `learner` and
   `guest`: `/api/notion/push` (the owner's Notion) and every `/api/eval/*`
   route (the owner's voice set). `/api/notion/queue` stays allowed: it writes
   the caller's own store. `/api/reminders/settings` is refused to guests only.
7. **Profile routes** (`eesti/api/profile.py`, registered in
   `eesti.api.ROUTERS`): `GET /api/me`, `POST /api/me`, `POST /api/me/reset`,
   `POST /api/me/restore`, `POST /api/guest/reset`.
8. **Learner directories.** `config.LEARNERS_DIR/<id>/` is created on first
   access, like the owner's files; on Cloud Run it is ephemeral and the
   learner's Durable Object restores it.

Nonowner content connections expose only shared source items. This applies to
listings, direct IDs, topic links, exam files and corpus-derived drills. Personal
sentence recordings also require the owner’s scope; public speech uses synthesis.

## Routes by scope

Every path in `eesti.api.paths()` is named in exactly one row;
`tests/test_guest_isolation.py::test_every_route_is_classified` compares the
table with the live FastAPI route inventory. “Own files” means the request's
permanent learner store; guest state routes are refused even when they name a
guest store. Worker-only sign-up, sign-in, sign-out, account-status and
owner-only account-removal routes are outside this FastAPI inventory.

| Class | owner | learner | guest | Routes |
|---|---|---|---|---|
| Back channel (`STATE_TOKEN`; 404 at Worker) | own files | own files | 403 | `/api/events`, `/api/events/import`, `/api/state/export`, `/api/state/import`, `/api/state/backup`, `/api/reminders` |
| Back channel, owner only | yes | 403 | 403 | `/api/content/export`, `/api/content/import`, `/api/progress/reset`, `/api/state/remove-account` |
| Answered by Worker from caller's object | yes | yes | 403 | `/api/push/key`, `/api/push/subscribe`, `/api/push/unsubscribe` |
| Owner only | yes | 403 | 403 | `/api/notion/push`, `/api/eval/available`, `/api/eval/clip`, `/api/eval/draft/{stem}`, `/api/eval/prompt`, `/api/eval/review/{stem}` |
| Permanent accounts only | yes | yes | 403 | `/api/me/reset`, `/api/me/restore`, `/api/reminders/settings` |
| Guest only | 403 | 403 | yes | `/api/guest/reset` |
| Shared material and page assets; learner data stays in the current scope | yes | yes | yes | `/`, `/api/auth/me`, `/api/course/topics/{topic}/skip`, `/api/learning/sentences`, `/api/me/onboarding`, `/api/placement/next`, `/api/asr`, `/api/asr/home`, `/api/check`, `/api/checkpoint/{level}`, `/api/checkpoint/{level}/result`, `/api/curriculum`, `/api/dictation/answer`, `/api/dictation/next`, `/api/engines`, `/api/enrich/{word}`, `/api/exam-spec/{level}`, `/api/exam/file/{item_id}`, `/api/exam/image/{item_id}/{page}/{index}`, `/api/exam/native/{item_id}`, `/api/exam/native/{item_id}/check`, `/api/exam/page/{item_id}/{page}`, `/api/exam/pages/{item_id}`, `/api/exam/text/{item_id}`, `/api/exam/{level}`, `/api/goal`, `/api/goal.ics`, `/api/health`, `/api/lesson/{topic}`, `/api/library`, `/api/library/{item_id}`, `/api/lookup/{word}`, `/api/me`, `/api/me/export`, `/api/milestones/{level}`, `/api/mine`, `/api/mock-run/{level}`, `/api/mock/{level}`, `/api/mock/{level}/{part}`, `/api/modes`, `/api/notion/pending`, `/api/notion/queue`, `/api/pack`, `/api/plan`, `/api/practice`, `/api/practice/answer`, `/api/pronounce`, `/api/read/answer`, `/api/read/questions/{item_id}`, `/api/readiness/{level}`, `/api/reading/next`, `/api/review`, `/api/review/grade`, `/api/review/stats`, `/api/sources`, `/api/speak`, `/api/speaking`, `/api/speaking/check`, `/api/speaking/feedback`, `/api/speaking/probe`, `/api/speaking/readaloud`, `/api/status`, `/api/testout/{topic}`, `/api/themes`, `/api/transcribe`, `/api/transcribe/text`, `/api/translate`, `/api/tutor`, `/api/vocab`, `/api/vocab/known`, `/app.css`, `/apple-touch-icon.png`, `/brand/{name}`, `/favicon.ico`, `/fonts/{name}`, `/icon.png`, `/icon.svg`, `/js/{name}`, `/manifest.webmanifest`, `/sw.js`, `/vendor/{name}` |

## Guest sandboxes

`eesti/guest.py`. A sandbox is `GUEST_DIR/<name>/` with the five learner files
and a `last-used` file whose mtime is the idle clock. `ensure` makes it and
writes the log's `backfill` marker; `sweep` (at most once a minute) drops
sandboxes idle over 24 h; beyond 50, the longest idle of those unused for an
hour, so a burst of new visitors never erases a guest mid-session; beyond 200,
the longest idle of any; `reset` removes one. Names come only from
`identity.sandbox_name`, so a name is always a safe single directory.

Agents and tests choose a sandbox with `x-eesti-guest: <name>` (Playwright:
`extraHTTPHeaders`). The Worker treats an explicit valid sandbox as guest traffic
even with a signed-in session or with an empty account registry; malformed
names are refused before forwarding. A browser without it gets a cookie. Start a run with
`POST /api/guest/reset` for a clean slate.

## Worker

`deploy/worker.ts`, with the account logic in `deploy/accounts.ts`.

1. **Accounts** (`deploy/accounts.ts`, stored by `LearnerState` named
   `singleton`, table `accounts(id, email UNIQUE, salt, hash, created, failures,
   locked_until)`):
   - `POST /api/auth/signup {email, password}`: email normalised to lower case
     and checked for shape and a 254-character maximum; passwords are 10–1024
     characters; refused (409, Russian
     message) only when the email is already taken. Public sign-up gets `l-` + 16 hex from `crypto.getRandomValues`. Sets the session and
     answers `{id, email, scope}`.
   - `POST /api/auth/login {email, password}`: constant-time compare; after 5
     failures the account waits 60 s; the same Russian message for unknown email
     and wrong password.
   - Account errors cross a Durable Object RPC boundary as serializable
     `name`, `status` and `message`, without the custom Error prototype. The
     Worker preserves validation (400), invalid credentials (401), duplicate
     signup (409) and temporary lockout (429); unexpected errors stay generic.
   - `POST /api/auth/logout`: clears the cookie. `GET /api/auth/me`: `{scope,
     id, email}` or `{scope: "guest"}`; with a configured secret,
     `signup_open` reports whether sessions are configured.
   - `POST /api/auth/bootstrap`: `STATE_TOKEN`-protected operator provisioning
     of the owner; returns 409 when an owner already exists.
   - `POST /api/auth/remove`: owner-only; after explicit confirmation, clears
     the learner's origin files and Durable Object state before removing the
     account row. A failed cleanup leaves the login in place so the request can
     be retried without orphaning data.
   - Session cookie `eesti_session`: `<id>.<expiry>.<hmac>` (HMAC-SHA-256 with
     `SESSION_SECRET`), `HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age` 90 days.
     Without `SESSION_SECRET`, account writes return 503, while `/me` and logout
     still work. Anonymous requests remain guests.
2. **Who.** Delete caller-sent `x-eesti-scope`,
   `x-eesti-learner` and `x-eesti-email` (`x-eesti-guest` may pass). A valid
   session for an existing account sets `x-eesti-scope` (`owner` or `learner`),
   `x-eesti-learner` (learners) and `x-eesti-email`. No valid session: `guest`
   regardless of account registry or session-secret configuration.
3. **Which object.** `stubFor(env, who)`: `singleton` for the owner,
   `learner:<id>` for a learner, none for a guest. The object remembers its `who`
   and `headers()` adds that scope to every back-channel call, so restore,
   snapshots, event pulls and reminders touch that learner's files only.
   `syncCorpus` runs in `singleton` only.
4. **Guests.** No personal object, snapshots or event pulls. Restore the shared
   corpus through the singleton (`restoreShared`, which never rebinds the
   owner's identity) before forwarding guest requests;
   `/api/push/*` → 403 with a Russian message.
5. **Speech.** `transcribe` forwards the caller's scope headers to
   `/api/transcribe/text` and pulls into the caller's object.
6. **Cron.** The nightly `BACKUP_CRON` copies each account's own log with its
   own scope headers. Otherwise `scheduled` reminds `singleton` and every learner account; an
   account restores only when its `next_check` has passed or it has new events
   (`docs/deploy.md` → Reminders).
7. **Back channel.** Every origin route guarded by `STATE_TOKEN` returns 404
   through the public Worker path.

### Deploy and operator steps

- Worker secret `SESSION_SECRET` is random, 32+ bytes.
  `.github/workflows/deploy.yml` pushes the secret like the others and warns
  (does not fail) when it is missing.
- Owner provisioning and public deployment: `docs/deploy.md`. Existing owner
  credentials remain valid; public sign-up always creates separate learner state.
- A forgotten password or removing an account: the operator procedure in
  `docs/deploy.md`.

## Profile

`GET /api/me` returns the shape documented in `eesti/profile.py` `summary`.
Sources, all existing:

| Field | From |
|---|---|
| `name` | newest `profile-set` event in the scope's log |
| `onboarding` | newest `onboarding-set` event: self-assessed start band, preferred first lane, skipped flag and timestamp |
| `email` | `identity.current().email` (the account's email; null for a guest) |
| `since` | the `joined` event (registration), else the first event other than `backfill` (a `legacy-row` counts: it is real history) |
| `last_active`, `active_days_28`, `rhythm` | `learner.daily_activity` and `learner.PRACTICE_EVENTS` |
| `level.current` | the level of `progress.resume`'s topic |
| `level.goal` | `exam.goal(progress)` |
| `level.checkpoints` | `checkpoint.passed_levels` |
| `milestones` | `milestones.for_level` for each of `config.LEVELS` |
| `totals` | `attempts` rows, `progress.mastered`, generator topics, review cards, `vocab` known |
| `restore_available`, `restore_at` | the latest reset marker not yet restored |

`POST /api/me {"name": …}` records `profile-set` (`profile.clean_name`: trimmed,
1–60 characters, blank clears). `POST /api/me/onboarding` records a self-assessed
start band and preferred first lane as `onboarding-set`, including in a guest
sandbox. Without `navigate`, it is a display recommendation. With `navigate`,
it moves the course past earlier chapters as reversible navigation, never
CEFR evidence, mastery or an exam result. An optional `explanation_language`
field prepares stable preferences for `ru`, `en` and `uk`; it does not make
unreviewed translations available. Email belongs to
the account, and dates and measured levels come from the evidence.

## Profile page

Content, so plain page and the shared treatment (`DESIGN.md` "Adding a page or
section", "Layout rhythm"); no glass, no new card, shadow, colour or streak.
Implementation: `eesti/web/js/profile.js`.

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
    Russian `detail`. The mobile dock stays hidden for the whole inline edit,
    so WebKit's input blur cannot cover Save/Cancel before a tap completes.
  - *E-post* (эл. почта): the account's email; for a guest, *puudub* (нет).
  - *Konto* (аккаунт): *Põhikonto* (основной, прогресс сохраняется),
    *Õppija* (ученик, свой прогресс сохраняется) or *Külaline* (гость,
    песочница), so everyone sees at once which account is signed in; with an
    account, *Logi välja* (выйти).
  - *Algus* (старт): the saved self-assessment and first lane, with *Muuda*
    (изменить). The Russian line says it is a recommendation, not a confirmed
    CEFR level.
    Skipping is shown as *Vahele jäetud* (вопросы пропущены), with the direct
    start links retained until the learner practises or chooses a recommendation.
  - *Õpib alates* (учится с: registration) and *Viimati* (последнее занятие): dates in
    Russian format; empty log → *Veel mitte* (пока нет).
  - *Raja tase* (уровень пути): current topic level, explicitly not an exam
    result; exam goal (level and date, or a link
    to Ülevaade to choose one), checkpoints passed.
- **Märgid** (значки): a level switch (`role="tablist"`, A1 · A2 · B1, the
  current level selected) over `sealsHtml(milestones[level])`.
- **Rütm** (ритм): `rhythmHtml(rhythm)` and *active days in the last four
  weeks*, exactly as Edenemine words it. The legend identifies each cell as a
  day and the whole grid as the last 12 weeks.
- **Kokku** (итого): attempts, topics mastered of total, review cards, known
  words, each as a number with a Russian label (`ruCount`).
- **Starting recommendation.** After account creation, two optional screens ask
  for a self-assessed starting band (A0 through A2–B1) and first lane: Rada,
  Sõnavara, Rääkimine or Eksam. The choice records `onboarding-set`, marks the
  recommended navigation destination, preselects the corresponding word level
  in free practice and Sõnavara, and opens the chosen real section. Skipping is
  also recorded so the question does not return. Every section remains open;
  the profile can change the choice. A learner with neither practice nor a saved
  choice retains the three direct start links.
- **Reset and restore progress.** Permanent accounts can use *Lähtesta
  edenemine* to clear
  attempts, milestones, exam goal and sections, review cards, vocabulary status,
  and queued corrections. It preserves the account, name and registration date.
  The page asks for confirmation and keeps a restore point in the event log.
  *Taasta edenemine* restores the state before the latest reset and includes
  practice recorded after it; name and account stay unchanged. A later reset
  replaces the previous restore point. `profile-progress-reset` and
  `profile-progress-restored` markers make reset/replay idempotent. The
  permanent-only `POST /api/me/reset` and `POST /api/me/restore` routes refuse
  guests with 403. Guests retain the separate confirmed sandbox reset, which
  also removes their sandbox name.
- **Guest.** A line at the top of every screen (not glass, not dismissible):
  *Külaline* and, in Russian, that this is a sandbox and progress will not be
  kept, with a link to Profiil to sign in. On the profile, *Tühjenda liivakast* (очистить песочницу) confirms before calling
  `POST /api/guest/reset`, then reloads the profile.
- **Sign-up and sign-in** (guests, on Profiil,
  above the rows): two
  views in a `role="tablist"`: *Logi sisse* (войти) and *Loo konto* (создать
  аккаунт, shown while `signup_open`). Fields *E-post*, *Parool* (пароль), and
  for a new account *Nimi*; one primary button each. After sign-up the page
  posts the name to `POST /api/me`. Signup, login and logout reload the document
  to discard every module's previous learner state. An unsuccessful name save
  after signup leaves a one-time notice on the new account's profile.
  Tabs preserve email/name drafts and keyboard focus; passwords are not kept
  across tab switches. *Näita/Peida* controls password visibility. Signup explains
  the ten-character minimum; login explains the existing operator-managed
  password recovery. Russian errors come from the server, with retry available.
  A note under *Loo konto* explains that the new account has its own progress.
  The introduction explains optional accounts and public guest use.
  If the account probe fails, profile evidence
  stays visible with *Proovi uuesti* instead of an unusable login form. Plain
  page, `autocomplete` attributes set, no glass.
- **Viewports.** Phone 402×874 and 874×402 (touch), iPad mini 744×1133, desktop
  1440×900, light and dark: no horizontal scroll, the name field and buttons at
  least 44px, the rail's own cards unchanged (the profile adds none).

## Verification

- `tests/test_identity.py` (done) — scope resolution and paths.
- `tests/test_guest_isolation.py`, `tests/test_learners.py` and
  `tests/test_profile.py` cover isolation, route scope and profile behavior.
- `tests/test_worker_accounts_contract.py` pins header replacement, guest
  object and push restrictions, learner ID shape, public sign-up and cron
  coverage. `tests/test_accounts.py` runs password, session, account creation
  and removal checks under Node.
- `tests/worker-auth.test.mjs` exercises real workerd Durable Object RPC for
  validation, indistinguishable invalid credentials, session cookies, logout,
  duplicate signup and lockout; `npm run test:worker` includes it.
- Browser journeys (`tests/test_e2e_journeys.py`) cover the profile tab,
  renaming, sign-up, sign-in, sign-out, the guest line and sandbox reset;
  onboarding, empty-profile start links and reset/restore confirmation are covered too;
  auth-tab focus, drafts, password visibility, auth-probe recovery, current-level
  milestones and document reloads on identity changes have regressions;
  journeys that write progress run in a guest sandbox by default.
