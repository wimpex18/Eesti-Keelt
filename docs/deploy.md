# Deploy and operate

| Part | Where | Why |
|---|---|---|
| App | **Google Cloud Run** (always-free tier), scales to zero | Vabamorf is a compiled C++ extension; Workers cannot run it, Cloudflare Containers need a paid plan |
| Front door | **Cloudflare Worker + Access** (free plan) | one login, state snapshots, Workers AI speech |

## Security: two doors, two locks

- Cloud Run allows unauthenticated invocations (required for the free tier), so
  its `run.app` URL is public. **`PROXY_TOKEN`**, known only to the Worker, is
  required on every request; without it the app answers 403. Unset (local
  `cli serve`) the guard is off. `/api/health` reports `origin_guarded`.
- **Cloudflare Access** guards the Worker with the *Cloudflare account* policy
  (never *Email domain*). The Worker also refuses any request without an Access
  identity; `ALLOW_UNAUTHENTICATED=1` is the deliberate escape hatch.
- `/api/state/*` requires `STATE_TOKEN` and is 404 from outside the Worker.

## Deploying

- **App:** merging to `main` is the deploy. A Cloud Build trigger builds the
  `Dockerfile` (word list, form index, EKI imports, `cli rections`) and deploys
  to Cloud Run in 10–15 minutes. `/api/health` reports `built` and `revision`.
- **Worker:** `.github/workflows/deploy.yml` runs on pushes to `main` touching
  `deploy/**`, `wrangler.jsonc`, `package*.json` or itself, and on demand. It
  typechecks, pushes Worker secrets and runs `wrangler deploy`.
- Build steps that reach third parties or optional files end in `||` so a
  missing file or a 403 costs one feature, not the image.

## Learner state across cold starts

Cloud Run disk is ephemeral. The app stamps every response with a boot id and
the evidence log's sequence number (`x-events-seq`). The Worker's SQLite-backed
Durable Object keeps two things: the **evidence log** (`eesti/evidence.py`), the
learner's source of truth, and a **snapshot** of the learner databases, which now
matters for the caches it carries (stored glosses, the provider breaker).

| When | What |
|---|---|
| new boot id | snapshot in (`POST /api/state/import`), then the whole log in batches (`POST /api/events/import`); the last batch settles: the instance rebuilds its learner tables from the log, or, the first time ever, backfills the log from them |
| any response whose `x-events-seq` is ahead | Worker copies the new events (`GET /api/events?after=`) |
| every 5 min, and ≤1/min after writes | Worker pulls a snapshot (`GET /api/state/export`) |

Events are keyed by id, so copying one twice changes nothing. On Cloud Run
(`EESTI_WORKER_RESTORES=1`, set in the Dockerfile) only that restore may start
the log: a write reaching an instance first, such as a speech transcript or
`reset-progress.sh`, gets 503 and records nothing. After a restore the Worker
resumes pulling from where the pushed log ended, so events the settle appended
(the first backfill) are copied too. The Durable Object
remembers which instance it restored and how far it copied, so being evicted from
memory does not trigger a second restore.

Safeguards:

- restore never overwrites a database that already has learner rows, and a
  failed restore is retried on the next request;
- until the serving instance is confirmed restored, the Worker answers every
  `/api/` request except `/api/health` with 503 and `Retry-After` (opening a
  text is a GET that records evidence) instead of recording into an empty copy;
- a snapshot is taken only from the instance the Worker restored (its boot id);
- an export with no learner rows (`learner_rows`) never replaces a snapshot
  that has some; a half-written snapshot counts as none;
- the service runs with `--max-instances 1` (set by `setup.sh`, checked by
  `check-service.sh`): a second instance would keep its own copy.

A crash before asynchronous event copying can lose acknowledged answers;
snapshots are an additional recovery copy, not a durability acknowledgement.

## EKI's recordings

`data/audio.db` (about 270 MB: word forms and read sentences, `eesti/haaldus.py`)
is too big for the image, which every build would carry, and far too big for the
Durable Object snapshot, which exists for a learner's progress. It lives in a
Cloud Storage bucket instead, mounted read-only into the container:

```bash
bash deploy/push-audio.sh            # upload and mount, in Cloud Shell
bash deploy/push-audio.sh --check    # what is there now
```

The service then reads it at `EESTI_AUDIO_DB`, and the Worker's edge cache keeps
whatever is actually played, so a word is fetched from the bucket once. Without
it `/api/pronounce` answers 404 and everything falls back to synthesis;
`/api/health` reports `recordings`.

## Reminders

The Worker sends them, because it holds the subscription and runs the cron; the
app decides what is worth saying, because it holds the evidence
(`eesti/reminders.py`). One VAPID key pair signs them.

```bash
python -m eesti.cli push-keys        # once, on your machine: writes .env, prints only the public key
bash deploy/set-push-keys.sh         # in Cloud Shell, with that .env
```

The cron runs hourly (`wrangler.jsonc` → `triggers.crons`) and asks
`/api/reminders`, a back-channel route guarded by `STATE_TOKEN`. What comes back
is a count and a fixed phrase — never a sentence the learner wrote — encrypted
to the subscription (RFC 8291) and signed with VAPID (RFC 8292). A tag keeps
one fact from arriving twice; a 404 or 410 from the push service drops the
subscription.

The Worker has all three VAPID bindings and its hourly cron configured. The
same pair is stored in repository secrets for the deploy workflow and privately
in the ignored `.env`.
Chrome on the owner's Mac is subscribed with permission granted;
delivery of an actual notification remains unverified. The smoke workflow
checks key configuration separately from browser delivery.

Without the keys the app says reminders are not configured and never asks the
browser for permission it cannot use. On iPhone, notifications work only from
the app added to the Home Screen (iOS 16.4+).

## The exam board's task files

`data/exam/` (about 130 MB of HARNO's task PDFs and listening recordings,
`cli harvest-exam --download`) travels the same way, for the same reason.

```bash
bash deploy/push-exam.sh            # sync and mount, in Cloud Shell
bash deploy/push-exam.sh --check    # what is there now
```

For native, page-aware task text and reviewed answer controls, run
`python -m eesti.cli prepare-exam --root data/exam` before the upload. It writes
private JSON sidecars beside task PDFs. `--ocr` uses locally installed
Tesseract with Estonian and English language data on sparse pages. The generated
files are git-ignored and travel with `push-exam.sh`; see `docs/exam-native.md`.

The service reads them at `EESTI_EXAM_DIR`. Two halves travel separately and
that is deliberate: the **text** extracted from each PDF is part of the library
(`push-content.sh`), so a task can be read on the deployment with no bucket at
all, while the **files** — above all the listening recordings, the half a text
cannot carry — need this mount. Where they are missing the catalogue says a
task is not downloaded and links out to harno.ee; `library._file_here` checks
rather than assumes, so the same database is honest on both machines.
If a catalogue row lacks `meta.file`, the app also checks the mounted path
derived from HARNO's URL using the downloader's filename rule.

## The reading corpus

Owner-only, so not in the image. Harvest locally and push; publication rebuilds
topic links against the current corpus. The
Worker archives it and restores it to every new container.

```bash
python -m eesti.cli harvest && python -m eesti.cli harvest-reading && python -m eesti.cli harvest-news
python -m eesti.cli harvest-exam --levels A2,B1 --download   # official tasks and their text
python -m eesti.cli link-topics                 # optional local preview
# In Cloud Shell, with content.db uploaded: build the publishing word list once.
python -m eesti.cli fetch-data && python -m eesti.cli build
bash deploy/push-content.sh data/content.db     # rebuilds links, then uploads
```

## Reference data in the image

All written into `data/eesti.db` at build, never snapshotted (a restore
replaces whole files):

| Step | Fills | `/api/health` `reference` field |
|---|---|---|
| `cli rections` | EKK SÜ 65 rections | `rections` |
| `cli import-levels deploy/eki/A1A2B1.txt` | official levels | `eki_levels` |
| `cli import-psv` / `import-evs` / `import-vsl` / `import-har` / `import-ekss` | EKI dictionaries | `eki_definitions`, `eki_russian`, `eki_loanwords`, `eki_terms`, `eki_explanatory` |

Smoke warns on any zero.

## Secrets

| Name | Cloud Run env | GitHub Actions | Purpose |
|---|---|---|---|
| `PROXY_TOKEN`, `STATE_TOKEN` | ✅ | ✅ | origin guard, snapshot endpoints (set by `setup.sh`) |
| `CLOUD_RUN_URL` | — | ✅ | where the Worker forwards |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | Workers AI token ✅ | deploy token ✅ | Worker deploy (Actions); grammar lane (Cloud Run) |
| `CLOUDFLARE_WORKERS_AI_TOKEN` | — | ✅ | Workers AI Read token for `eval.yml` |
| `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`, `WORKER_URL` | — | ✅ | smoke test service token |
| `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY` | ✅ | ✅ | grammar lanes; Actions copies for the eval |
| `HF_TOKEN` | optional | — | hosted Whisper fallback for speech |
| `EKILEX_API_KEY` | ✅ | — | live Ekilex word card |
| `NOTION_TOKEN` | ✅ | — | sending corrections to `Vead` |

A key read by the container must be on Cloud Run; one stored only as a Worker
secret is invisible to the app and fails silently.

## Operator scripts (Google Cloud Shell)

Always start from a fresh clone — the scripts read allowed key names from
`eesti/env.py`:

```bash
cd ~ && (git clone https://github.com/wimpex18/Eesti-Keelt.git 2>/dev/null || true) && cd Eesti-Keelt && git pull
```

| Script | Does |
|---|---|
| `deploy/setup.sh` | one-time wiring: generates tokens, sets them on Cloud Run and in Actions, verifies 403/200. Re-running rotates tokens — then run `gh workflow run deploy.yml` or every request 403s |
| `deploy/set-llm-key.sh NAME` | sets any `KNOWN_KEYS` variable on Cloud Run with hidden input, and verifies it landed |
| `deploy/check-service.sh` | lists variable names on each service (never values), flags missing ones and traffic on an old revision |
| `deploy/push-content.sh FILE` | uploads the harvested corpus to the origin |
| `deploy/reset-progress.sh <topic> \| --everything` | forgets one topic's practice history, or all of it, on the deployment |

If `gcloud` has no project: `gcloud config set project <id>`.

## Verifying production

A session cannot read the deployed app. Use the **`smoke`** workflow
(Actions → smoke → Run workflow). It runs after `deploy`, daily, and on demand,
and checks: Access closed, health, readable EKI audio and HARNO exam files,
image build stamp vs `main`, origin guard, speech, reference counts, live
dictionary, library and topic links.

- Wait until the image is newer than the merge (10–15 min), or smoke reports on
  the previous image — it prints which.
- `grammar explains … configured` only reads configuration. Run with
  **`deep: true`** after any provider or key change: it sends one sentence and
  prints which engine answered, or the per-lane failure diagnostics.

## First-time Cloudflare notes

- Open **Workers & Pages** once before the first deploy, or `wrangler deploy`
  fails with code 10063 (no `workers.dev` subdomain).
- Enable Access as soon as the first deploy is green. For a zero-length gap,
  deploy without `CLOUD_RUN_URL` (Worker answers 503), enable Access, then add
  the secret and re-run.

## Cost

The intended single-learner workload uses free allocations, not a guaranteed
zero-cost SLA. Workers AI Whisper is listed at about $0.0005/audio minute
inside a shared daily allocation; see `docs/asr-evaluation.md`. Monitor actual
Cloud Run/storage/build and account-wide AI usage; no paid inference host is
part of the chosen architecture.

## Backup, recovery and erasure

The Durable Object's copied log and snapshots are live replication in the same
hosting account. They are not an independent backup and the write response is
not a durable acknowledgement: copying uses `waitUntil`. An origin crash before
the copy can lose acknowledged answers. Snapshot intervals concern operational
caches as well as legacy learner state; they do not bound every event-loss case.
Keep one writable revision/instance; do not scale this design horizontally.

Before a state migration or redesign, download `Minu andmed`
(`/api/me/export`) while signed in and save the JSONL privately outside the
hosting account. Repeat periodically during study; there is no nightly export.
It contains learner writing and transcripts, never raw production audio. Verify:

```bash
python -m eesti.cli verify-backup /private/path/eesti-keelt-events.jsonl
```

This replays twice into temporary databases, checks stable projections, refuses
unknown/unreplayable events or a missing backfill marker, and leaves live state
untouched. It proves replayability, not authenticity or that the server export
was complete at a particular time. It does not restore dictionary caches, push
subscriptions, the private library, exam/audio mounts or recordings. Those need
their original sources or separate private backups. Keep exports out of public
Actions artifacts and git. Losing the hosting account means losing work since
the most recent independent export.

For a real recovery, first stop learner traffic/cron and preserve the current
state. Validate the chosen export with the matching code version, restore into
an isolated local checkout and inspect the reconstructed state. Production
replacement must replace the DO authority and origin together; uploading only
the origin log is insufficient because the DO can restore the other copy.
There is no coordinated production overwrite command. Cloudflare's
SQLite-backed DO recovery facilities are an additional account-local option,
not a substitute for a tested off-account export.

`reset-progress.sh --everything` resets practice; it does **not erase personal
data**. For owner-requested erasure, take the app offline, stop cron and revoke
push subscriptions, purge the singleton DO's log/snapshot/push state, replace
the origin's learner databases, clear browser IndexedDB and service-worker
storage on every used device, and delete private exports/eval audio separately.
Remove any chosen Notion exports in Notion and address provider-retained data
under each provider's terms. Do not reopen until both restore authority and
origin are empty; otherwise restore can resurrect the history. This is an
operator procedure, not an implemented `DELETE /api/me` promise. That endpoint
remains deferred until coordinated erasure and recovery-retention semantics
are implemented and tested end to end (ADR-0005).
