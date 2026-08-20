# Setup: where the API key actually goes

Short answer: **a GitHub Actions secret, now.** A Cloudflare Worker secret later,
once the app is deployed. Not Supabase, and not the Claude cloud environment box.

The reason it is not obvious is that "the project" lives in three places — a
GitHub repo, an ephemeral cloud dev container, and (eventually) Cloudflare — and
a secret belongs wherever the code that uses it runs.

## Where **not** to put it

**Not the Claude "cloud environment" variables box.** That panel says it plainly:
*"These are visible to anyone using this environment — don't add secrets or
credentials."* It is for `NODE_ENV`-style configuration, not keys.

**Not Supabase.** Supabase secrets are for Supabase Edge Functions. That is
WanderAlt's stack; this project does not use Supabase at all.

**Not a `.env` in the cloud session.** The container is ephemeral — it is
reclaimed after inactivity, and anything written there is gone. My earlier
instructions assumed local development and were wrong for this setup.

**Not in a chat message, an issue, or a commit.** If a key is ever exposed,
revoke it at `openrouter.ai/keys`; revoking is instant and free.

## Where to put it now: GitHub Actions

This is the right home today, because the thing that needs the key is the
**model eval** — and the eval is most useful run automatically, with its result
attached to a pull request rather than to one throwaway terminal.

1. Go to **https://github.com/wimpex18/Eesti-Keelt/settings/secrets/actions**
2. **New repository secret**
3. Name: `OPENROUTER_API_KEY` — Secret: paste the key — **Add secret**

That is it. GitHub encrypts it, never shows it again, and masks it in logs.

### Running the eval

**Actions** tab → **Estonian model eval** → **Run workflow**, then pick a
provider and optionally a model id. Leave the model blank to score the pinned
default.

If no key is configured the workflow still passes — the model-id check is worth
running on its own — but it emits a **warning** and its summary says in as many
words that **no model was scored**. A green tick there never means "the model is
good"; check the run summary for numbers.

```
recall     0.9   caught 9/10        # planted errors found
precision  1.0   left alone 8/8     # correct sentences not flagged
```

Precision is the number to watch. A checker that flags every partitive scores
perfect recall and is worse than useless — it would teach you that every
partitive is wrong. That is why 8 of the 18 cases are already-correct Estonian.

Run it against two or three models and compare. That is the whole reason to
prefer OpenRouter: one key reaches 412 models, so the choice can be made on
evidence rather than on a recommendation.

The workflow also checks the **pinned model id still exists** before scoring —
ids get withdrawn silently, and a withdrawn `:free` id is the nastiest case
because the paid one with the same name keeps working.

## Where it goes later: Cloudflare

You do **not** need a Cloudflare project yet — nothing is deployed. When we get
there, the key becomes a Worker secret:

```bash
npx wrangler secret put OPENROUTER_API_KEY
```

Encrypted at rest, injected at runtime, never in `wrangler.toml` and never in
the repo. Setting up Cloudflare will mean: a Workers & Pages project, a D1
database for the exported dataset, an R2 bucket for cached audio, and
**Cloudflare Access** in front of it — which is not optional, because it is what
keeps the owner-only material (HARNO exam tasks, ERR transcripts) private on a
public URL.

## If you ever do work locally

Clone the repo and use a git-ignored `.env`:

```bash
cp .env.example .env      # paste the key after OPENROUTER_API_KEY=
python -m eesti.cli keys  # prints only the last 4 characters
```

`.env` is git-ignored; `.env.example` is the committed file and holds no values.

## Summary

| Where the code runs | Where the key goes |
|---|---|
| GitHub Actions (eval, CI) | **repo secret** ← do this now |
| Cloudflare Worker (production) | `wrangler secret put` ← later |
| Your own machine | git-ignored `.env` |
| This cloud dev session | nowhere — it is ephemeral |

## Optional extras

| Key | What it adds | Where to get it |
|---|---|---|
| `GROQ_API_KEY` | fastest inference, generous free tier | https://console.groq.com/keys |
| `ANTHROPIC_API_KEY` | paid quality backstop | https://console.anthropic.com |
| `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | Workers AI — runs inside Cloudflare, 10 000 neurons/day | Cloudflare dashboard → My Profile → API Tokens |
| `NOTION_TOKEN` | push confirmed errors into the `Vead` database | https://www.notion.so/my-integrations |

Add any of them as repository secrets the same way. The provider chain tries each
in order and skips the ones that are missing, so adding a key is the entire
configuration step.

## Speech recognition (optional)

The speaking tab records and plays back with no key at all. For a transcript,
the cheapest and best-fitting route is the one the app already deploys to:

    CLOUDFLARE_API_TOKEN   # already needed for the Workers AI eval
    CLOUDFLARE_ACCOUNT_ID

That runs `@cf/openai/whisper-large-v3-turbo` with the language pinned to
Estonian, at $0.00051 per audio minute. `OPENROUTER_API_KEY` works as a
fallback. (`HF_TOKEN` no longer does: the HuggingFace lane pointed at a router
that serves no Estonian model, and was replaced by `LOCAL_LLM_URL` — a server
you run yourself. See [`docs/local-llm.md`](local-llm.md).) See [`docs/speaking.md`](speaking.md) for why an Estonian LLM
cannot do this job and which Estonian speech model would, if anyone hosted it.
