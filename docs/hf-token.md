# Turning on the Estonian model — what `HF_TOKEN` is and where to put it

Everything for the EstLLM lane is written and wired. One thing is missing, and
it is not code: a Hugging Face token. This is the whole procedure.

## What you are turning on

`tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125` — Llama 3.1 with Estonian-adapted
weights, from the University of Tartu. It is the model this project would rather
explain Estonian with than any general free model, and the Hugging Face router
is the only way to reach it without owning a machine.

It changes **explanations only**. Drills, grading, the study order and the
mastery gate stay deterministic code, exactly as `docs/ai-boundaries.md` says.
Nothing about what is correct depends on this token.

## What it is not

It is not a purchase and not a subscription. It is a read token on a free
account. Hugging Face routes the request on to `featherless-ai`, and *that*
provider's own free and paid tiers decide what happens when you use it a lot —
which is why the honest answer below is "measure it", not "it is free".

## Step 1 — get the token (5 minutes, once)

1. Sign in or sign up at <https://huggingface.co>.
2. Go to **Settings → Access Tokens** (<https://huggingface.co/settings/tokens>).
3. **Create new token**, type **Read**. Name it something you will recognise in
   a year — `eesti-keelt` does fine.
4. Copy it. It starts `hf_` and it is shown **once**.

Leave the page open until step 2 is done. If you lose it, delete that token and
make another; there is no way to read it back.

## Step 2 — decide which of the three places need it

There are three, they are independent, and you do not need all of them. Pick by
what you want to happen.

| You want | Put it in | How |
|---|---|---|
| the deployed app to explain corrections in Estonian-adapted prose | **Cloud Run** env var | `bash deploy/set-llm-key.sh HF_TOKEN` in Cloud Shell |
| a **score** — how the model actually does on Estonian, against the others | **GitHub Actions** secret | `gh secret set HF_TOKEN --repo wimpex18/Eesti-Keelt` |
| `python -m eesti.cli serve` on your own machine to use it | a git-ignored **`.env`** | add a line `HF_TOKEN=hf_...` |

If you only do one, do the **middle** one. Until a real request completes, this
lane is a plan and not a result — see "What is still unproven" below.

**Never** paste the token into a chat with me, into a commit, or into the Claude
environment-variables box. Those three destinations are the whole rule; all
three commands above take the value without it passing through this session.

### Cloud Run, in detail

Open Cloud Shell in the Google Cloud console, in this project, then:

```bash
bash deploy/set-llm-key.sh HF_TOKEN
```

It prompts for the value with the echo off, hands it to `gcloud` on stdin — so
it reaches neither your shell history nor the process table — starts a new
revision, and then reads the variable *names* back off the service that is
actually serving traffic to confirm it took. It never prints the value. If
traffic has not moved to the new revision it says so and gives you the one
command that moves it.

### GitHub Actions, in detail

From anywhere you are signed in to `gh`:

```bash
gh secret set HF_TOKEN --repo wimpex18/Eesti-Keelt
```

It reads the value from your terminal. `.github/workflows/eval.yml` already
passes `secrets.HF_TOKEN` through as `HF_TOKEN`, so nothing else changes.

### Locally, in detail

`.env` is in `.gitignore` and `eesti/env.py` loads it. One line:

```
HF_TOKEN=hf_...
```

No `export`, no quotes — `env.py` strips a stray `export ` and skips a name it
could not read back, but the plain form is the one that works everywhere.

## Step 3 — get the number

This is the step the whole thing is for.

Run the **eval** workflow from the Actions tab with **provider: `huggingface`**,
and leave the model on `(provider default)` so it uses the pinned EstLLM id.
Compare its score against the runs already on record for `openrouter` and
`groq`.

Locally, the same thing:

```bash
python -m eesti.cli eval --provider huggingface
```

Two things to expect the first time. The model may be **cold**, and a first
request can time out while it loads — run it again before concluding anything.
And a score that is *worse* than a general model is a real result, not a
failure of the setup: it would mean the Estonian-adapted weights do not help on
this task, which is worth knowing and is exactly why the lane was wired instead
of assumed.

## Step 4 — check it landed

```bash
python -m eesti.cli keys
```

reports presence and a masked tail — enough to confirm the right key is loaded
without putting it on screen.

For the deployment, run the **smoke** workflow with **`deep: true`**. The cheap
line only reads configuration: `grammar explains ........ configured` is true of
a provider whose quota is spent. Only the deep check sends a sentence, and only
it can tell you the chain answers.

## What is still unproven, and why the docs say so

That a request completes. The Hugging Face router answers **401 before it
routes**, so an unauthenticated probe from here returns 401 for a real model id
and for an invented one alike — it proves nothing either way. What *is* verified
from this repository is that the model's own metadata reports `featherless-ai`,
status `live`, task `conversational`, and that the router speaks the OpenAI
shape this client already sends.

That gap is deliberate: this repository must never hold a token, so the last
step cannot happen here. Step 3 is what closes it.

## If you would rather not

Nothing breaks. An absent key disables its lane and nothing else —
`LLM_PREFERENCE` falls through to `openrouter`, `groq`, `workers-ai`, and below
those to Vabamorf's offline mode, which still finds object-case candidates and
typos without any network at all. The Estonian model is an improvement to reach
for, not a dependency.

There is also a lane with no token at all: `local`, the same EstLLM weights as a
GGUF served by Ollama or llama.cpp on your own machine. `docs/local-llm.md` has
that setup. It costs a download instead of a signup, and nobody else can read
the requests.
