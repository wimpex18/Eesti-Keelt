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

## Access is not optional, and the Worker enforces it

`browse(..., public_only=True)` returns **0** owner-only items, which is the app
being honest; it is not what keeps the URL private. **Cloudflare Access is.**

Access tab on the Worker → **All traffic** → the **Cloudflare account** policy,
which means "members of this account" and on a one-person account means you.
Not **Email domain**: that grants everyone at the domain, and on a `gmail.com`
address it grants the internet.

But a dashboard setting is a thing that can be switched off by accident, reset
by a later change, or never have applied at all — which is what happened on the
first attempt here. The policy was created, *Apply Access* was pressed, and an
anonymous request kept returning 200 for a quarter of an hour. Nothing
complained, because nothing was watching.

So the Worker **refuses every request that did not come through Access**. The
runtime attaches an identity to requests that passed it; without one, the Worker
answers 403 with the instructions rather than the app. Losing the policy is now
a locked door instead of a silent opening.

`ALLOW_UNAUTHENTICATED=1` serves without Access on purpose. It is deliberately
awkward, because the default has to be the safe one — the unsafe one is
invisible.

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
| `OPENROUTER_API_KEY` | ✅ env var | — | grammar explanations; **Cloud Run only** |

**Which half reads which is not a detail.** The Worker and the container read
different variables, and putting one in the wrong half fails silently — nothing
errors, the value simply is not there, and the feature drops into its fallback.

That happened with `OPENROUTER_API_KEY`. It is read by `eesti/providers/llm.py`,
which runs in the container; it was stored as a Worker secret, where nothing
reads it. The grammar checker sat permanently in offline mode, so no correction
carried a fix, no "log it" button rendered, and nothing ever reached the Notion
log — a whole chain inert because a credential was one hop from the process that
needed it. And it was the worse half of the trade: all the exposure of holding a
key, none of the benefit.

Set it where it belongs, without it touching your shell history:

```bash
bash deploy/set-llm-key.sh
```

The script now reads the variable's **name** back off the service afterwards
and refuses to claim success if it is not there — because a run of it once
ended with the key still absent, and the only symptom was corrections quietly
arriving without explanations.

The same script sets any key the app reads, not only the grammar one — the
allowed names come from `eesti/env.py`, so there is no second list to drift:

```bash
bash deploy/set-llm-key.sh NOTION_TOKEN
```

`NOTION_TOKEN` is what lets confirmed corrections actually reach the `Vead`
database. Without it they queue in the app and the send button says so rather
than failing when pressed.

To ask what a deployment is currently configured with, changing nothing:

```bash
bash deploy/check-service.sh
```

It lists every Cloud Run service in the project with the environment variable
**names** it carries (never a value), flags the four whose absence is silent,
and warns when traffic is still on an older revision than the one a variable
was set on — which is the way a correctly-run `set-llm-key.sh` can still leave
the app in offline mode.

From outside, the same question is answered by `/api/engines`, and the `deep`
input on the **smoke** workflow sends one real sentence through the chain to
prove the key works rather than merely exists.

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

## Before the first deploy: open the Workers page once

A Cloudflare account has no `*.workers.dev` subdomain until somebody opens the
Workers section of the dashboard, and until it does, `wrangler deploy` fails
with:

```
✘ [ERROR] You need a workers.dev subdomain in order to proceed. [code: 10063]
```

It is not a permissions problem and no amount of retrying fixes it. Open
**Workers & Pages** in the dashboard once — the subdomain is created on that
first visit — then re-run the deploy workflow.

Worth knowing what this failure does *not* mean: the run that hit it had already
uploaded every secret and bundled the Worker successfully. Only the final upload
failed, so a re-run after the click is all that is needed.

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

**Merging to `main` is the deploy.** There is no command to run. Cloud Build
triggers on `main`, builds this `Dockerfile` — including `RUN python -m
eesti.cli export`, which is where the generated dataset comes from — and
deploys the result to Cloud Run. `PROXY_TOKEN` and `STATE_TOKEN` are
environment variables on the service, set once by `deploy/setup.sh`.

### `setup.sh` is not a deploy command

It is one-time wiring, and re-running it takes the app down until a second
thing happens. It rotates both tokens into Cloud Run and GitHub Actions
secrets — but **not** into the Cloudflare Worker, which receives them from the
`deploy` workflow through `wrangler secret put`. Until that workflow runs, the
Worker offers the old `PROXY_TOKEN` to an origin that has already changed it
and every request 403s.

The workflow fires on a push to `main` touching `deploy/**`, `wrangler.jsonc`,
`package*.json` or itself. A token rotation touches none of those, so after
rotating, trigger it yourself:

```
gh workflow run deploy.yml --repo wimpex18/Eesti-Keelt
```

This was written down because it was got wrong: `setup.sh` was recommended as
the way to ship a Python change, which would have rotated the tokens, skipped
the Worker, and deployed nothing.

**The Worker and the app deploy by different routes.** The `deploy` workflow
going green means the *Worker* is current; it says nothing about the container.
A Python change merged to `main` reaches the learner only once Cloud Build has
rebuilt and redeployed the image — which takes 10–15 minutes, and which nothing
in this repository can observe.

So the image stamps itself. `/api/health` reports `built` (when the image was
built) and `revision` (the commit, if the builder passed one), and the smoke
test prints it. That is how you tell a stale image from a missing feature —
a distinction that cost real time before the stamp existed.

To include the commit, add a build arg on the trigger:

```
--build-arg BUILD_REV=$COMMIT_SHA
```

Without it the timestamp still answers the question that matters.

The image builds the derived databases from the public CC-BY-SA wordlist, so it
is reproducible from scratch and nothing owner-only is baked in. **The first
build takes 10–15 minutes**: it installs EstNLTK (~170 MB) and generates the
46 MB form index inside the build.

One build step is allowed to fail. `cli rections` fetches EKK's rection table
from EKI, which has already returned 403 to a datacenter IP once; chained with
the offline steps it would take the whole image down with it. It runs in its own
layer and logs a warning. The cost is one topic — `rektsioon` says "run `cli
rections` once" — against an unbuildable image.

## Speech runs on the Worker, not the origin

Cloudflare Workers AI is reachable two ways: over REST with an API token, or
through the Worker's own `AI` binding. This uses the binding, and the reason is
authority rather than convenience — the only token template that covers Workers
can also **edit** them, which is far more than "turn this audio into words"
deserves to hold on the origin.

So `POST /api/transcribe` is answered by the Worker: Whisper
(`@cf/openai/whisper-large-v3-turbo`), `language` pinned to `et` rather than
guessed, and the question being answered passed as `initial_prompt` because a
few seconds of accented Estonian is exactly what a recogniser guesses wrong on.

The transcript then goes to `POST /api/transcribe/text` on the app, which owns
every judgement made about it. **A model says what it heard; nothing else in
this app is a model's opinion.** The target sentence is known, so the comparison
is string alignment, and it never travels without the caveat saying a miss may
be the recogniser rather than the learner.

`/api/transcribe` still works locally under `cli serve`, where there is no
Worker and the provider chain does the recognising.

One consequence worth knowing: the origin cannot see the binding, so its
`/api/asr` reports every hosted engine as absent. The Worker corrects that one
field on the way past — it is the only place that knows.

## The reading library: harvested once, pushed once

The corpus is **not** in the image, for two reasons that both matter.
Re-running the ERR and Selges keeles harvest on every build would hammer
someone else's server for nothing; and that material is owner-only by licence,
so it has no business inside an image built from a public repository.

Cloud Run's disk is ephemeral too, so a file copied into a container is gone at
the next cold start. It therefore travels the same road as the learner's
progress: pushed once, archived by the Worker, handed back to every container
that starts afterwards.

```bash
# on your laptop, once
python -m eesti.cli harvest
python -m eesti.cli harvest-reading
python -m eesti.cli link-topics     # which texts demonstrate which topic

# then in Cloud Shell, with data/content.db uploaded
bash deploy/push-content.sh data/content.db
```

**Why the push targets Cloud Run and not the Worker.** Cloudflare Access guards
the Worker, and Access is an interactive login — a script cannot satisfy one.
The origin is guarded by `PROXY_TOKEN`, which a script *can* send. So the
harvest goes to the origin, and the Worker archives it from there.

`push-content.sh` reads both tokens straight out of the running Cloud Run
service, so you never see or type either one.

The Worker then keeps the two in step, in whichever direction is needed:

| Container | Archive | What happens |
|---|---|---|
| has one | empty | **archived** — a fresh push becomes permanent |
| empty | has one | **restored** — every cold start after that |
| agree | agree | nothing |

Without a corpus the reading library is simply empty and everything else works
— the generators that need corpus sentences return nothing rather than failing,
which is the same degradation the CLI has. `/api/health` reports `library` so
the two are distinguishable.

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
