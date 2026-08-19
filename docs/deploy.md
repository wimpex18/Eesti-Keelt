# Deploying

Two halves, on two providers, for one reason each.

| Half | Where | Why there |
|---|---|---|
| the app | **Google Cloud Run** | it needs Vabamorf, a compiled C++ Python extension |
| the front door | **Cloudflare Worker + Access** | one hostname, one login, and Workers AI for speech |

## Why the app is not a Worker

An earlier plan in this repo said: export everything to D1, serve it from a
Worker. That described the app as it was — a lookup tool over a pre-computed
form index. It is not this app any more.

`cloze`, `conjugation`, `patterns` and `verbs` all call **Vabamorf at request
time**, because drills are *generated*, not stored: the conditional of a verb is
synthesised when you ask for it, and a cloze is cut from a corpus sentence
analysed on the spot. Vabamorf is a compiled C++ Python extension. Workers run
JavaScript and WASM. There is no version of that plan that works.

## Why the app is not in a Cloudflare Container either

Cloudflare Containers would have solved it in one place — and the first version
of this file recommended exactly that. It requires the **Workers Paid plan, $5 a
month**, which this project does not spend. Cloud Run's always-free tier (2M
requests, 360k GiB-seconds, 180k vCPU-seconds per month) runs the same
`Dockerfile` for nothing, and one learner practising daily is not close to those
numbers. A card is required for identity verification; the free tier is not a
trial and does not expire.

So the container moved, and the Worker stayed — as a doorman.

## The two doors problem

Cloud Run must **allow unauthenticated invocations** for this to be free. That
means its `run.app` URL answers the entire internet. Cloudflare Access sits in
front of the **Worker**, not in front of that URL.

Left there, Access would guard one of two doors, and roughly **421 owner-only
harvested items** — ERR transcripts are © ERR, Selges keeles carries no reuse
grant — would be a hostname guess away from being published.

So there is a second lock. `PROXY_TOKEN` is a secret only the Worker holds; it
is sent on every proxied request, and the app refuses anything without it:

- **Unset** → the guard is off. That is deliberate: the ordinary way to run this
  app is `cli serve` on a laptop, and demanding a token there is ceremony.
- **Set** → every request without a matching header gets 403, `/` included. A
  reader who can fetch the page can read the library through it.

`/api/health` reports `origin_guarded`, so "is the deployment actually closed?"
is a question with an answer you can check rather than assume.

## The thing that would have eaten your progress

Cloud Run disk is **ephemeral** and the service scales to zero. A fresh instance
starts with the image's databases and none of the learner's. Mastery, review
queue and vocabulary are SQLite files on that disk, so without the snapshotting
below, **a lunch break would reset everything the curriculum exists to
accumulate** — silently, which is the worst way for it to happen.

Cloud Run gives the Worker no shutdown hook to observe, so restarts are
**noticed, not announced**: the app stamps every response with a boot id, and a
boot id the Worker has not seen means a new, empty instance.

| When | What happens |
|---|---|
| boot id changes | the Worker pushes the last snapshot in (`POST /api/state/import`) |
| every 5 minutes | a Durable Object alarm pulls a snapshot out (`GET /api/state/export`) |
| after any write | a snapshot, debounced to at most one a minute |

Only the learner's three databases travel. The word list, the form index and the
harvested corpus are derived or baked into the image, so shipping them would be
58 MB of copying nothing.

The snapshot lives in a **SQLite-backed Durable Object**, which Cloudflare made
available on the **Workers Free plan** in April 2025 — free-plan limits are 5M
rows read and 100k rows written per day, against a snapshot that costs a handful
of rows. It is stored in 96 KiB chunks with the index key written **last**, so
an interrupted save leaves the previous snapshot unreadable rather than leaving
a truncated one that looks fine.

Four deliberate refusals in that path:

- **Restore never overwrites a database that already has learner rows.** A
  restore racing a learner who has started answering would discard the newer
  work; losing minutes beats losing it silently.
- **A half-written snapshot is treated as no snapshot**, rather than restored
  over a working database.
- **An empty export never overwrites a real snapshot.**
- **The snapshot endpoints refuse when `STATE_TOKEN` is unset**, and the Worker
  404s `/api/state/*` from the outside — they are its back channel, not a route.
  An unset secret is a misconfiguration, not permission.

### Verified, not assumed

The image was built and run before any of this was recommended, which is how the
next bug was found rather than discovered in production:

| Check | Result |
|---|---|
| image builds | 1.08 GB |
| app starts, `/api/health` | 160 316 words indexed |
| Vabamorf generates in-container | `Ta ____, kui saaks.` (tingiv) |
| answer recorded | `accuracy: 1.0`, gate `8/10` |
| snapshot survives container destroy → recreate | attempt count 1 → 1 |

**The bug that found.** The restore refused every time: `{"restored": [],
"skipped": ["progress"]}`. The guard against overwriting live data tested
"database exists and is non-empty", and a fresh container's very first request
creates `progress.db` *with its schema* — so an untouched instance looked like
one with work in it, and the snapshot was silently discarded. The guard now asks
whether the database holds **learner rows**, which is what "live data" was
always supposed to mean.

That failure mode is worth naming: the mechanism protecting progress would have
thrown progress away, quietly, and only under the exact conditions of a real
deploy.

**The residual risk, stated plainly:** a crash between snapshots loses up to a
few minutes of answers. The alternative is moving learner state to D1, which is
a real rewrite of the storage layer and is not worth it for that.

## Access is not optional

`browse(..., public_only=True)` returns **0** owner-only items, which is the app
being honest; it is not what keeps the URL private. **Cloudflare Access is.**

Zero Trust → Access → Applications → Self-hosted → the Worker's hostname → one
policy allowing your own email. Set it up before the first deploy, not after.

## Secrets, and where each one lives

Nothing here belongs in the repo, in a chat message, or in an environment
variable box that says it is visible to others.

| Secret | Cloud Run | GitHub Actions | What it is |
|---|---|---|---|
| `PROXY_TOKEN` | ✅ env var | ✅ repo secret | shared; closes the second door |
| `STATE_TOKEN` | ✅ env var | ✅ repo secret | guards the snapshot endpoints |
| `CLOUD_RUN_URL` | — | ✅ repo secret | where the Worker forwards |
| `CLOUDFLARE_API_TOKEN` | — | ✅ repo secret | deploys the Worker |
| `CLOUDFLARE_ACCOUNT_ID` | — | ✅ repo secret | ditto |
| `OPENROUTER_API_KEY` | ✅ env var | optional | grammar explanations; optional |

`PROXY_TOKEN` and `STATE_TOKEN` are values you invent — any long random string,
the same string in both places:

```bash
openssl rand -hex 32
```

## One script does the wiring

`deploy/setup.sh`, run once in **Google Cloud Shell** — the terminal icon in the
Cloud Console. Cloud Shell is already signed in to your Google account and ships
`gcloud`, `openssl` and `gh`, so there is nothing to install and no password to
type.

```bash
git clone https://github.com/wimpex18/Eesti-Keelt.git
cd Eesti-Keelt
bash deploy/setup.sh
```

It generates both tokens, sets them on the Cloud Run service, looks the service
URL up rather than asking you for it, stores all three as GitHub Actions
secrets, and then checks the guard actually took effect: an unauthorised request
to the app must come back **403**, an authorised one **200**. It prints nothing
secret and writes nothing to disk.

Only the two Cloudflare values are left by hand, because minting a credential is
not something a script should do on your behalf.

## The window between deploying and enabling Access

Cloudflare Access can only be switched on for a Worker that **already exists**,
so there is a gap between the deploy finishing and the toggle being flipped —
and the Worker supplies `PROXY_TOKEN` itself, so anyone who reaches it in that
gap is all the way in. The hostname is not published anywhere, and the gap is
however long it takes you to click, so the practical answer is: **enable Access
as soon as the deploy workflow goes green**, before opening the app yourself.

If you would rather the gap be exactly zero, the workflow allows it:
`CLOUD_RUN_URL` is the only secret it does not require. Deploy without it and
the Worker answers 503 to everyone; enable Access; then add the secret and
re-run. The app is reachable for the first time already behind Access.

## Deploying the Worker

`.github/workflows/deploy.yml` does it on every push to `main` that touches the
Worker, and on demand from the Actions tab. It typechecks, pushes the Worker
secrets, then deploys. A missing repository secret fails the run with a sentence
naming it, because that is the most likely reason it ever goes red and the fix
is a settings page rather than a code change.

By hand, if you'd rather:

```bash
npm ci
npx wrangler secret put CLOUD_RUN_URL
npx wrangler secret put PROXY_TOKEN
npx wrangler secret put STATE_TOKEN
npx wrangler deploy
```

## Deploying the app

Cloud Build trigger on `main` → builds this `Dockerfile` → deploys to Cloud Run.
Set `PROXY_TOKEN` and `STATE_TOKEN` as environment variables on the service.

The image builds the derived databases from the public CC-BY-SA wordlist, so it
is reproducible from scratch and nothing owner-only is baked in. **The first
build takes 10–15 minutes**: it installs EstNLTK (~170 MB) and generates the
46 MB form index inside the build.

One build step is allowed to fail. `cli rections` fetches EKK's rection table
from EKI, which has already returned 403 to a datacenter IP once; chained with
the offline steps it would take the whole image down with it. It runs in its own
layer and logs a warning. The cost is one topic — `rektsioon` says "run `cli
rections` once" — against an unbuildable image.

## The reading library needs one manual step

The harvested corpus is **not** in the image, for two reasons: re-running the
ERR and Selges keeles harvest on every build would hammer someone else's server
for no reason, and that material is owner-only, so it has no business inside a
distributable image.

Harvest once locally, then supply `content.db` at runtime via `EESTI_CONTENT_DB`
(the `Dockerfile` declares `/app/data/content`). Without it the reading library
is simply empty and everything else works — the generators that need corpus
sentences return nothing rather than failing, which is the same degradation the
CLI has.

## What it costs

For one learner, nothing, and the shape is worth knowing:

- **Cloud Run**: within the always-free tier. It scales to zero, so a daily
  practice session is minutes of CPU, not hours. Cold start is a few seconds.
- **Worker + Durable Object**: within the free plan.
- **Speech**: `@cf/openai/whisper-large-v3-turbo` at **$0.00051 per audio
  minute** — Workers AI has a free daily allocation, and a learner reading
  sentences aloud does not approach it.
- **Grammar explanations**: a free-tier model on OpenRouter, or nothing — the
  app degrades to offline Vabamorf evidence.
