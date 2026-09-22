# Local setup and API keys

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m eesti.cli fetch-data      # word list, ~2.8 MB, once
.venv/bin/python -m eesti.cli build           # import and index
.venv/bin/python -m eesti.cli export          # form index for the word card
.venv/bin/python -m eesti.cli rections        # EKK's rection table, once
.venv/bin/python -m eesti.cli harvest-reading # reading texts (Selges keeles)
.venv/bin/python -m eesti.cli harvest-news    # ERR's weekly Lihtsad uudised
.venv/bin/python -m eesti.cli harvest         # ERR Raadio 4 archives
.venv/bin/python -m eesti.cli harvest-exam --levels A2,B1 --download
.venv/bin/python -m eesti.cli link-topics     # texts -> the topics they show
.venv/bin/python -m eesti.cli serve           # http://127.0.0.1:8000
```

`rektsioon` drills need `cli rections`, and the library is empty until the
harvests run: each one says what it stored.

HTTPS is verified against certifi's bundle rather than the platform's store
(`eesti/tls.py`), because a python.org build on macOS could not verify EKI's
archive and a source that will not verify looks exactly like one that is down.

Without any key: drills, grading, the path, reading, review and vocabulary all
work; the writing check uses Vabamorf offline evidence.

For tests: `.venv/bin/pip install pytest pytest-xdist` and, for the browser
journeys, `.venv/bin/playwright install chromium webkit`.

Two things are deliberately not installed by default:

```bash
python -m eesti.cli push-keys                  # reminders: one VAPID pair, into .env
.venv/bin/pip install "fsrs[optimizer]"        # only to run `cli optimise-review`
```

`fsrs[optimizer]` pulls in torch and pandas — hundreds of megabytes for a job
run once there are about 1 000 reviews, so it stays out of the image and out of
the default install.

## Where a key goes

A secret belongs where the code that reads it runs.

| Code runs in | Put the key in |
|---|---|
| Your machine | git-ignored `.env` (copy `.env.example`); check with `cli keys`, which prints only the last characters |
| GitHub Actions (eval, smoke) | repository secret: Settings → Secrets and variables → Actions |
| The deployed app | Cloud Run env var via `bash deploy/set-llm-key.sh NAME` in Cloud Shell |

Never in chat, a commit, an issue or the Claude environment-variables box. In
`.env`, write `NAME=value` (a leading `export ` is stripped).

## Keys the app reads

`eesti/env.py` `KNOWN_KEYS` is the list; `set-llm-key.sh` and
`check-service.sh` read it from there.

| Key | Enables | Get it |
|---|---|---|
| `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | Workers AI grammar lane (token needs **Account → Workers AI → Read** only) | dash.cloudflare.com → My Profile → API Tokens; account ID is in the dashboard URL |
| `NVIDIA_API_KEY` | NVIDIA explicit evaluation (GLM-5.3-Flash; not automatic routing) | build.nvidia.com → Get API Key |
| `MISTRAL_API_KEY` | Mistral lane (Experiment plan, phone verification) | console.mistral.ai → API Keys |
| `OPENROUTER_API_KEY` | OpenRouter free models | openrouter.ai/keys |
| `HF_TOKEN` | hosted Whisper fallback for speech | huggingface.co/settings/tokens |
| `EKILEX_API_KEY` | EKI's Ekilex API for the word card | your profile at ekilex.ee |
| `NOTION_TOKEN` | sending corrections to the `Vead` database | notion.so/my-integrations |

Also read when set: `LOCAL_LLM_URL` / `LOCAL_LLM_MODEL` (local model server),
`<LANE>_MODEL` (override a pinned model). See `docs/ai-providers.md`.
