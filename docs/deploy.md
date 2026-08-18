# Deploying to Cloudflare

## Why this is a container and not a Worker

An earlier plan in this repo said: export everything to D1, serve it from a
Worker. That described the app as it was — a lookup tool over a pre-computed
form index. It is not this app any more.

`cloze`, `conjugation`, `patterns` and `verbs` all call **Vabamorf at request
time**, because drills are *generated*, not stored: the conditional of a verb is
synthesised when you ask for it, and a cloze is cut from a corpus sentence that
is analysed on the spot. Vabamorf is a compiled C++ Python extension. Workers
run JavaScript and WASM. There is no version of that plan that works.

**Cloudflare Containers** solves it directly: a Worker fronts a real Linux
container running the FastAPI app, so nothing has to be rewritten and the app
still lives on Cloudflare, behind Access, on HTTPS — which is also what makes
the microphone work, since `getUserMedia` requires a secure context.

## The thing that would have eaten your progress

Container disk is **ephemeral**. From Cloudflare's own FAQ: *"All disk is
ephemeral. When a Container instance goes to sleep, the next time it is started,
it will have a fresh disk as defined by its container image."*

The learner's mastery, review queue and vocabulary are SQLite files on that
disk. With a ten-minute sleep timer, **every coffee break would have reset
everything steps 3–9 exist to accumulate** — silently, which is the worst way
for it to happen.

So the durable copy lives in the Durable Object that manages the container:

| When | What happens |
|---|---|
| container starts | the Worker pushes the last snapshot in (`POST /api/state/import`) |
| every 5 minutes | an alarm pulls a snapshot out (`GET /api/state/export`) |
| before sleeping | `onActivityExpired` snapshots, *then* stops |

Only the learner's three databases travel. The word list, the form index and the
harvested corpus are derived or baked into the image, so shipping them would be
58 MB of copying nothing.

Two deliberate refusals in that path:

- **Restore never overwrites a database that already has content.** A restore
  racing a learner who has already started answering would discard the newer
  work; losing five minutes beats losing it silently.
- **The snapshot endpoints refuse when `STATE_TOKEN` is unset**, rather than
  defaulting to open. An unset secret is a misconfiguration, not permission.

### Verified, not assumed

The image was built and run before any of this was recommended, which is how the
next bug was found rather than discovered in production:

| Check | Result |
|---|---|
| image builds | 1.08 GB |
| app starts, `/api/health` | 160 316 words indexed |
| Vabamorf generates in-container | `Ta ____, kui saaks.` (tingiv) |
| answer recorded | `accuracy: 1.0`, gate `8/10` |
| **snapshot survives container destroy → recreate** | attempt count 1 → 1 |

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

**The residual risk, stated plainly:** a crash between snapshots loses up to
five minutes of answers. Cloudflare's docs mention disk snapshots "coming soon";
until then, the alternative is moving learner state to D1, which is a real
rewrite of the storage layer and is not worth it for five minutes.

## Access is not optional

Roughly **421 of the harvested items are owner-only by licence** — ERR
transcripts are © ERR, Selges keeles carries no reuse grant. `browse(...,
public_only=True)` returns **0** of them, which is the app being honest; it is
not what keeps the URL private. **Cloudflare Access is.** Deploying without an
Access policy publishes someone else's copyrighted material.

Set it up before the first deploy, not after: Zero Trust → Access → Applications
→ Self-hosted, the Worker's hostname, one policy allowing your own email.

## Deploying

```bash
npm install -g wrangler
npm install @cloudflare/containers

wrangler secret put STATE_TOKEN            # any long random string
wrangler secret put CLOUDFLARE_API_TOKEN   # Workers AI, for speech
wrangler secret put CLOUDFLARE_ACCOUNT_ID
wrangler secret put OPENROUTER_API_KEY     # optional: grammar explanations

wrangler deploy
```

The image builds the derived databases from the public CC-BY-SA wordlist, so it
is reproducible from scratch and nothing owner-only is baked in.

## The reading library needs one manual step

The harvested corpus is **not** in the image, for two reasons: re-running the
ERR and Selges keeles harvest on every build would hammer someone else's server
for no reason, and that material is owner-only, so it has no business inside a
distributable image.

Harvest once locally, then supply `content.db` at runtime via the volume in the
`Dockerfile` (`EESTI_CONTENT_DB`). Without it the reading library is simply
empty and everything else works — the generators that need corpus sentences
return nothing rather than failing, which is the same degradation the CLI has.

## What it costs

For one learner, essentially nothing, and the shape is worth knowing:

- **Container**: billed on actual CPU used ($0.00002/vCPU-second) plus
  provisioned memory and disk while running. It sleeps after ten minutes idle,
  so a daily practice session is minutes of runtime, not hours.
- **Speech**: `@cf/openai/whisper-large-v3-turbo` at **$0.00051 per audio
  minute**.
- **Grammar explanations**: a free-tier model on OpenRouter, or nothing — the
  app degrades to offline Vabamorf evidence.

`standard-1` (½ vCPU, 4 GiB, 8 GB disk) rather than `basic`: EstNLTK wants more
than the 1 GiB `basic` provides once the form index is loaded, and OOM in
Containers means a restart, which means a snapshot restore.
