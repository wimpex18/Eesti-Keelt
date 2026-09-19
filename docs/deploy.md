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

A crash between snapshots can lose a few minutes of answers.

## The reading corpus

Owner-only, so not in the image. Harvest locally, link topics, push once; the
Worker archives it and restores it to every new container.

```bash
python -m eesti.cli harvest && python -m eesti.cli harvest-reading && python -m eesti.cli harvest-news
python -m eesti.cli link-topics                 # required — fills the topic join
bash deploy/push-content.sh data/content.db     # in Cloud Shell, with the file uploaded
```

## Reference data in the image

All written into `data/eesti.db` at build, never snapshotted (a restore
replaces whole files):

| Step | Fills | `/api/health` `reference` field |
|---|---|---|
| `cli rections` | EKK SÜ 64 rections | `rections` |
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
and checks: Access closed, health, image build stamp vs `main`, origin guard,
speech, reference counts, live dictionary, library and topic links.

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

Nothing for one learner: Cloud Run and the Worker stay within free tiers;
Workers AI Whisper is $0.00051/audio minute inside a free daily allocation; the
grammar lanes are free tiers.
