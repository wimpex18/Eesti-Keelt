# Deploy and operate

| Part | Where | Why |
|---|---|---|
| App | **Google Cloud Run** (always-free tier), scales to zero | Vabamorf is a compiled C++ extension; Workers cannot run it, Cloudflare Containers need a paid plan |
| Front door | **Public Cloudflare Worker** (free plan) | optional in-app login, state snapshots, speech |
| Speech | the owner's **Mac mini** (home service) through a Cloudflare Tunnel, **Workers AI** Whisper as fallback | TalTech's Estonian model hears the learner far better; no free host can run it |

## Public entry and protected origin

Visitors open Grove without a login gate. Unsigned visitors get isolated guest
progress; optional in-app accounts keep each learner’s progress across devices.
The Worker rebuilds identity headers from its signed session, never from caller
claims. Personal corpus imports remain available only to the owner.

Cloud Run requires `PROXY_TOKEN` on every request. Without it the origin answers
403. Local `cli serve` has no guard unless the token is configured.
`/api/state/*` also requires `STATE_TOKEN` and is 404 through the public Worker.

## Deploying

- **App:** merging to `main` is the deploy. A Cloud Build trigger builds the
  `Dockerfile` (word list, form index, EKI imports, `cli rections`) and deploys
  to Cloud Run in 10–15 minutes. `/api/health` reports `built` and `revision`.
- **Worker:** `.github/workflows/deploy.yml` runs on pushes to `main` touching
  `deploy/**`, `wrangler.jsonc`, `package*.json` or itself, and on demand. It
  typechecks, pushes Worker secrets and runs `wrangler deploy`.
- Build steps that reach third parties or optional files end in `||` so a
  missing file or a 403 costs one feature, not the image.

## In-app accounts

Configure `SESSION_SECRET` in repository **Settings → Secrets and variables →
Actions**. Generate at least 32 random bytes in a trusted terminal (for example,
`openssl rand -hex 32`) and save them directly as the secret. Deployment pushes
it to the Worker. Without it, public guest practice and `/api/auth/me` remain
available; sign-up and sign-in return 503.

Public **Profiil → Loo konto** creates a learner with separate progress.
Existing owner credentials and the `singleton` object remain valid. If an owner
login has never been provisioned, run `python3 deploy/create-owner.py` in a
trusted terminal with `WORKER_URL` and `STATE_TOKEN` supplied from the secret
store. It prompts for email/password without echoing the password. The protected
`POST /api/auth/bootstrap` provisions `owner` once, independently of public
sign-up. An existing owner needs no migration.

There is no self-service password recovery. For a forgotten password:

1. In a trusted local terminal, run `node --experimental-strip-types
   deploy/reset-account-password.ts` with Node 24. It prompts for the account
   email and a replacement password without echoing the password, then prints
   one `UPDATE` statement.
2. In the Cloudflare dashboard, open **Workers & Pages → Durable Objects**,
   select the `LEARNER_STATE` namespace, open **Data Studio**, select the object
   named `singleton`, and run the generated statement. It replaces the hash and
   clears that account's failed-login delay.
3. If the reset follows a suspected session compromise, rotate `SESSION_SECRET`
   in GitHub Actions and redeploy the Worker. That signs out every account;
   progress is kept.

To remove a learner account and permanently delete its progress:

1. In the `singleton` Data Studio, run
   `SELECT id, email, created FROM accounts ORDER BY created, id;` and copy the
   learner's `l-…` id. Do not use `owner`.
2. While signed in to the app as the owner, open the browser's developer
   console and submit the removal with that exact id:

   ```js
   fetch("/api/auth/remove", {
     method: "POST",
     headers: {"Content-Type": "application/json"},
     body: JSON.stringify({id: "l-…", confirm: true})
   }).then(r => r.json())
   ```

   The Worker requires the owner session, clears the learner's current origin
   files and Durable Object data (events, snapshots and subscriptions), then
   removes the account row. This cannot be undone. If cleanup returns 503, the
   account remains available; retry with the same id.
3. Delete the learner's nightly copies in Cloud Shell:
   `gcloud storage rm -r gs://<bucket>/events/l-…/`. The origin can only add
   objects there, so it cannot do this itself; deleted objects stay
   recoverable for the bucket's soft-delete window.

## Learner state across cold starts

Cloud Run disk is ephemeral. The app stamps every response with a boot id and
the evidence log's sequence number (`x-events-seq`). The Worker's SQLite-backed
Durable Object keeps two things: the **evidence log** (`eesti/evidence.py`), the
learner's source of truth, and a **snapshot** of the learner databases, which now
matters for the caches it carries (stored glosses, the provider breaker).

| When | What |
|---|---|
| new boot id | snapshot in (`POST /api/state/import`), then the whole log in batches (`POST /api/events/import`); the last batch settles: the instance rebuilds its learner tables from the log, or, the first time ever, backfills the log from them |
| any successful response whose `x-events-seq` is ahead | Worker copies the new events (`GET /api/events?after=`) and returns success only after the Durable Object reaches that sequence for the response's boot id |
| every 5 min, and ≤1/min after writes | Worker pulls a snapshot (`GET /api/state/export`) |

Events are keyed by id, so copying one twice changes nothing. Outside the
minute-long liveness window the Worker asks `/api/health?live=1`, which answers
the boot id and corpus revision without counting the word list or recordings.
The owner object records the revision of the corpus it archived with the
archive, so a container that already holds it, after an eviction or a cold
restore, is neither exported nor archived again. Guest and learner requests
restore that shared corpus through the owner object without rebinding its
identity. On Cloud Run
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
- event copying is retried briefly and a success is replaced by a retriable 503
  if the Durable Object cannot confirm the sequence for that response's boot id;
  online drill and review retries reuse their event id and therefore cannot
  count twice;
- the service runs with `--max-instances 1` (set by `setup.sh`, checked by
  `check-service.sh`): a second instance would keep its own copy.

For the event log, a successful API response is a durability
acknowledgement. A request that receives the explicit 503 may already have
reached the origin, so refresh its state before repeating a lower-frequency
action. The visible drill and review retry controls are safe to use directly:
they preserve one event id and one submitted answer. The request was not
reported as safely saved until the Durable Object confirmed it.
Snapshots remain an additional recovery copy for caches and projections, not
the acknowledgement.

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
`/api/health` reports `recordings`, counted once per version of the file. The
Worker's liveness probe, `/api/health?live=1`, reads only the boot id and the
corpus revision.

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

The answer also names `next_check`, the earliest moment anything new could be
due (`reminders.next_check`): a new local day, the learner's chosen hour, the
moment the review queue reaches its threshold, each moved past quiet hours.
Until then, and while no new event has reached its Durable Object, a
subscribed account's cron pass neither wakes nor restores the origin. It asks
again after at most six hours, after any new evidence, and in the next hour
when a push service refused a reminder.

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
Worker archives it and restores it to every new container. A corpus checksum
changes independently of the origin boot, so uploading to a warm instance also
updates the archive. Chunk generations publish through a final pointer; a
failed replacement retains the previous usable archive.

```bash
python -m eesti.cli harvest && python -m eesti.cli harvest-reading && python -m eesti.cli harvest-news
python -m eesti.cli harvest-exam --levels A2,B1 --download   # official tasks and their text
python -m eesti.cli link-topics                 # optional local preview
# In Cloud Shell, with content.db uploaded: build the publishing word list once.
python -m eesti.cli fetch-data && python -m eesti.cli build
bash deploy/push-content.sh data/content.db     # rebuilds links, then uploads
```

After uploading, open `/api/health` through the front door **as the owner**.
This explicit check bypasses the ordinary one-minute liveness cache. Confirm
that `corpus_revision` and `corpus_archived_revision` are equal and non-null;
retry the check if necessary before closing the publishing session. The origin
alone cannot attest the Durable Object copy. Publish refreshed exam files with
`deploy/push-exam.sh` as well, then run the `smoke` workflow with `deep: true`.

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
| `SESSION_SECRET` | — | Worker secret ✅ | signs account sessions; generate 32 random bytes or more |
| `CLOUD_RUN_URL` | — | ✅ | where the Worker forwards |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | Workers AI token ✅ | deploy token ✅ | Worker deploy (Actions); grammar lane (Cloud Run) |
| `CLOUDFLARE_WORKERS_AI_TOKEN` | — | ✅ | Workers AI Read token for `eval.yml` |
| `WORKER_URL` | — | ✅ | public-entry verification and anonymous smoke |
| `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY` | ✅ | ✅ | grammar lanes; Actions copies for the eval |
| `HOME_ASR_TOKEN` | — | Worker secret (dashboard) | proves a recording came from the Worker to the Mac mini home service |
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
| `deploy/setup-backup.sh` | creates the private backup bucket, deletes copies after `RETAIN_DAYS` (180), grants the service account object-create only, sets `EESTI_BACKUP_BUCKET`; safe to re-run |
| `deploy/check-service.sh` | lists variable names on each service (never values), flags missing ones and traffic on an old revision |
| `deploy/push-content.sh FILE` | uploads the harvested corpus to the origin |
| `deploy/reset-progress.sh <topic> \| --everything` | forgets one topic's practice history, or all of it, on the deployment |

If `gcloud` has no project: `gcloud config set project <id>`.

## Verifying production

Use the **`smoke`** workflow for repeatable deployment checks
(Actions → smoke → Run workflow). It runs after `deploy`, daily, and on demand,
and checks: public shell, anonymous guest identity, health, readable EKI audio,
image build stamp vs `main`, origin guard, speech, reference counts, live
dictionary, library and topic links.

Smoke first asks the Worker account endpoint and origin profile to confirm a
named guest sandbox. If either disagrees, the run fails and sends no grammar
sample. It also checks that the home speech binding is configured; an offline
Mac is a warning because Cloudflare fallback is intentional.

- Wait until the image is newer than the merge (10–15 min), or smoke reports on
  the previous image — it prints which.
- `grammar explains … configured` only reads configuration. Run with
  **`deep: true`** after any provider or key change: it sends one sentence and
  generated reference audio in the guest sandbox and prints which engines
  answered, or the per-lane failure diagnostics. The speech sample proves
  routing and authentication, not recognition quality.

## Home speech service

`deploy/home-asr/README.md`: a Cloudflare Tunnel from the Mac mini, a Workers
VPC Service on it (`vpc_services` in `wrangler.jsonc`, binding `HOME_ASR`), the
`HOME_ASR_TOKEN` Worker secret, and `deploy/home-asr/install.sh` on the Mac.
The `deploy` workflow's token needs permission to bind VPC Services
(Connectivity Directory Bind). It checks access to each configured service
before pushing secrets. In Cloudflare **Manage account → Account API tokens**,
edit the deployment token's account policy, add **Connectivity Directory →
Bind**, review and save. Keep its existing permissions; an existing token's
permission update needs no replacement GitHub secret. Then run **Actions →
deploy → Run workflow**. Check it from the speaking page ("Сейчас тебя
слушает твой Mac mini") or on the Mac: `curl http://127.0.0.1:8790/health`.

## First-time Cloudflare notes

- Open **Workers & Pages** once before the first deploy, or `wrangler deploy`
  fails with code 10063 (no `workers.dev` subdomain).
- Set `WORKER_URL` to the existing `https://…workers.dev` URL, together with
  `CLOUD_RUN_URL`, `PROXY_TOKEN`, `STATE_TOKEN` and the Cloudflare deployment
  credentials. The token also needs **Account → Access: Apps and Policies →
  Write** for the public-entry migration.
- After Worker deployment, `deploy/open-public-access.py` waits for Cloud Run’s
  `public_access: true` health marker before removing the login gate for this
  exact hostname. It leaves unrelated and wildcard applications untouched,
  refuses applications shared with other domains, then verifies anonymous
  shell, health and guest identity. A failed migration fails the deploy workflow;
  correct the reported configuration and rerun it. Smoke requires only
  `WORKER_URL`, with no external login credentials.

## Cost

The typical practice workload uses free allocations, not a guaranteed
zero-cost SLA. Workers AI Whisper, the speech fallback, is listed at about
$0.0005/audio minute inside a shared daily allocation. The home service costs
the Mac mini's electricity; Tunnels and Workers VPC are free. Monitor Cloud
Run/storage/build and account-wide AI usage; no paid inference host is part of
the architecture.

## Backup, recovery and erasure

The Durable Object's copied log and snapshots are live replication in the same
hosting account. They are not an independent backup. Successful permanent-account
responses wait until the event log reaches the Durable Object; snapshots remain
asynchronous because they hold projections and caches, not the replay authority.
Keep one writable revision/instance; do not scale this design horizontally.

Every night (`BACKUP_CRON`, 01:37 UTC) each permanent account's Durable
Object sends its whole event log, gzipped and in replay order, to the
back-channel route `POST /api/state/backup`. The origin replays it strictly in
temporary stores, in a separate process (`cli verify-backup`), and only a log
that replays is written to the private bucket named by `EESTI_BACKUP_BUCKET`
as `events/<account>/YYYY/MM/DD/<time>-<sha256>.jsonl.gz` (`eesti/backup.py`).
The upload uses the Cloud Run service account's own identity and never
replaces an existing object. A refused or failed copy is logged by the Worker
("learner backup not stored") and recorded in the object's `backup-last`;
the next night tries again. Set it up once in Cloud Shell:

```bash
bash deploy/setup-backup.sh      # bucket, 180-day lifecycle, object-create grant, env
```

The service account receives object-create on the bucket and nothing else
there; project-wide roles it already holds still apply, and the script lists
them. Storage is Google's at-rest encryption on a private bucket: anyone with
read access to the bucket can read learner writing and transcripts. To check
a copy yourself, download it into a private folder and run `verify-backup` on
the `.jsonl.gz` as it is. There is no disaster-restore endpoint; a restore
from a copy is a coordinated operator procedure (below).

A learner can also download `Minu andmed` (`/api/me/export`) while signed in
and save the JSONL privately. Exports and nightly copies contain learner
writing and transcripts, never raw production audio. Verify either:

```bash
python -m eesti.cli verify-backup /private/path/eesti-keelt-events.jsonl
```

This replays twice into temporary databases, checks stable projections, refuses
unknown/unreplayable events or a missing backfill marker, and leaves live state
untouched. It proves replayability, not authenticity or that the server export
was complete at a particular time. It does not restore dictionary caches, push
subscriptions, the private library, exam/audio mounts or recordings. Those need
their original sources or separate private backups. Keep exports out of public
Actions artifacts and git. Cloudflare's SQLite-backed recovery remains a useful
account-local option, not a substitute for a private export outside the hosting
account. A production restore must coordinate the origin and its Durable Object
so the next request cannot overwrite the restored history.

`reset-progress.sh --everything` resets practice; it does **not erase personal
data**. For owner-requested erasure, take the app offline, stop cron and revoke
push subscriptions, purge the singleton DO's log/snapshot/push state, replace
the origin's learner databases, clear browser IndexedDB and service-worker
storage on every used device, delete the account's nightly copies
(`gcloud storage rm -r gs://<bucket>/events/<account>/`), and delete private
exports/eval audio separately. Remove any chosen Notion exports in Notion and
address provider-retained data
under each provider's terms. Do not reopen until both restore authority and
origin are empty; otherwise restore can resurrect the history. This is an
operator procedure, not an implemented `DELETE /api/me` promise. That endpoint
remains deferred until coordinated erasure and recovery-retention semantics
are implemented and tested end to end (ADR-0005).
