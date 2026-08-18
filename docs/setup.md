# Setup: API keys

None of the keys below are required. Without any of them the app still runs:
vocabulary, morphology, drill generation, grading, TTS and the harvested reading
material all work, because they depend on data this project owns.

What a key adds is the **free-text writing check** — judging whether a sentence
you wrote is right, and explaining why in Russian. That is the one job with no
deterministic substitute.

## Which key to get

**OpenRouter.** One key, 412 models, 15 of them free. It is recommended over a
single-vendor key for a reason beyond convenience: it lets you run the eval
across several models and pick on evidence.

```bash
python -m eesti.cli eval --provider openrouter --model <id>
```

Estonian is low-resource, so "good at English" does not imply "good at Estonian",
and the specific judgement here — genitive for a completed whole object,
partitive for ongoing, partial or negated — is exactly the language-specific
semantics that thins out first. Being able to compare is worth more than any
recommendation, including the one in `ai-strategy.md`.

### Getting it

1. Go to **https://openrouter.ai** and sign in (GitHub or Google works).
2. Open **https://openrouter.ai/keys**.
3. **Create Key**, name it something like `eesti-keelt`, copy the value.

Free tier is **50 requests/day**. If you later want more, a **one-time $10**
purchase raises it to **1 000/day** — that is an account threshold, not
consumption; the `:free` models still price at zero and the balance just sits
there. At a few checks a day you will not come close to needing it.

## Where to put it

**Locally** — a git-ignored `.env` in the project root:

```bash
cp .env.example .env
# then edit .env and paste the key after the = sign
```

```
OPENROUTER_API_KEY=sk-or-v1-...
```

Confirm it loaded — this prints only the last four characters, never the key:

```bash
python -m eesti.cli keys
```

```
 ✓ OPENROUTER_API_KEY       …a1b2      OpenRouter — 412 models, 15 free.
```

**On Cloudflare**, once deployed — as a Worker secret, never in `wrangler.toml`:

```bash
npx wrangler secret put OPENROUTER_API_KEY
```

## Rules

- **`.env` is git-ignored and must stay that way.** `.env.example` is the file
  that gets committed, and it holds no values.
- **Never paste a key into a chat, an issue or a commit message.** If one is ever
  exposed, revoke it at `openrouter.ai/keys` and issue a new one — revoking is
  instant and costs nothing.
- The app only ever reads keys from the environment, and nothing in it prints a
  key. `cli keys` masks to the last four characters on purpose.

## Optional extras

| Key | What it adds | Where |
|---|---|---|
| `GROQ_API_KEY` | fastest inference, generous free tier | https://console.groq.com/keys |
| `ANTHROPIC_API_KEY` | paid quality backstop | https://console.anthropic.com |
| `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | Workers AI — runs inside Cloudflare, no egress, 10 000 neurons/day | Cloudflare dashboard → My Profile → API Tokens |
| `NOTION_TOKEN` | push confirmed errors into the existing `Vead` database | https://www.notion.so/my-integrations |

Set several and the provider chain tries them in order, skipping any that are
missing — so adding a key is the whole configuration step.
