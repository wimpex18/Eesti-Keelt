# AI providers

Each lane has a day's allowance (`providers/budget.py`), set under the
provider's published limit and counted in `progress.db`, so a cold start cannot
spend a 50-a-day quota four times over. A lane whose allowance is spent is
skipped like a failing one, and `/api/engines` reports what is left.

Grammar checks and origin-side speech recognition go through a chain of
interchangeable providers with a shared circuit breaker (`providers/breaker.py`:
skip a lane after 2 failures for 15 min, doubling up to 6 days, persisted in
`progress.db`). Translation, TTS and the Worker's speech recognition are single
engines without a breaker. Missing keys are skipped, not failures. Responses
name the engine that answered.

## Grammar chain

`providers/grammar.py` builds: **TartuNLP GEC** → LLM lanes in
`LLM_PREFERENCE` → **Neurotõlge est→est** → **Vabamorf offline** (always
answers: object-case candidates and spelling, no explanations).

- **TartuNLP GEC** (`api.tartunlp.ai/grammar`) fronts a Llammas 7B model on
  the University of Tartu cluster. While that backend does not answer, the
  breaker steps over the lane; it stays in the chain for when it returns.
- **Neurotõlge est→est** (`tartunlp-mt`) runs TartuNLP's translation service
  from Estonian to Estonian, which normalises the sentence. It paraphrases as
  well, so only one-for-one substitutions of the same lemma with the same
  number survive, and a genitive ↔ partitive swap only after a negation. It
  gives no explanation. Eval: precision 1.0, recall 0.1 on the 18 cases,
  whose errors are mostly the aspect swaps it refuses to judge.
- TartuNLP's terms say both services store what they are sent. Deterministic spelling, agreement
and rection checks are merged into every answer.

LLM lanes (`providers/llm.py`, all OpenAI-compatible, all free):

| Order | Lane | Default model | Key(s) | Free limit | Measured |
|---|---|---|---|---|---|
| 1 | `local` | EstLLM 8B GGUF via Ollama | `LOCAL_LLM_URL` | unmetered, your machine | — |
| 2 | `workers-ai` | `@cf/openai/gpt-oss-120b` | `CLOUDFLARE_API_TOKEN` (Workers AI Read) + `CLOUDFLARE_ACCOUNT_ID` | 10 000 neurons/day | P 1.0 · R 0.8 · 3–8 s |
| 3 | `nvidia` | `z-ai/glm-5.3-flash` | `NVIDIA_API_KEY` | 40 req/min | P 1.0 · R 1.0 · 20–60 s, 1 of 18 timed out |
| 4 | `mistral` | `mistral-large-latest` | `MISTRAL_API_KEY` | Experiment plan, ~1B tokens/month | P 1.0 · R 0.3 · 1–4 s |
| 5 | `openrouter` | `dots-studio/dots-3-note-preview:free` | `OPENROUTER_API_KEY` | 50 req/day, failures count | P 1.0 · R 0.71 |

**Order = recall at precision 1.0, weighed against how long the learner
waits.** NVIDIA gives the best answer but is too slow to go first. Mistral
leads Tartu's human-vote Estonian leaderboard for fluency yet mostly answers
"no errors" on this task, so fluency does not decide the order.

Override a pinned model without a deploy: set `<LANE>_MODEL` (e.g.
`WORKERS_AI_MODEL`, `LOCAL_LLM_MODEL`) on Cloud Run with
`deploy/set-llm-key.sh`.

### Local EstLLM

Run an OpenAI-compatible server (e.g. Ollama with the GGUF above) and set
`LOCAL_LLM_URL`. To reach it from the deployment, expose it through a tunnel and
set the URL on Cloud Run. It is private and free, and only as available as the
machine.

## Choosing a model: the eval

`eesti/evals/gec.py` — 18 Estonian sentences: 10 with a planted error
(**recall**) and 8 already correct (**precision**). Precision matters more: a
checker that flags every partitive teaches the wrong rule. Exits non-zero below
0.8 on either score; exit 2 means nothing was measured.

```bash
python -m eesti.cli models --provider nvidia --limit 10   # is the pinned id still live?
python -m eesti.cli eval --provider nvidia --model z-ai/glm-5.3-flash
```

In CI: **Actions → Estonian model eval** (`eval.yml`), choose a provider and a
model. It runs weekly on OpenRouter only. The model menu may contain only
`:free` ids or a lane's pinned default (`test_every_selectable_model_is_free`).
A green run with "not measured" in the summary is not a pass.

Model ids are withdrawn without notice (a withdrawn id answers 404, 403 or
410). Check the catalogue before pinning, and re-run the eval after any change
of pin.

## Prompts

One system prompt reaches every lane, from an 8B model to a large one. Lines
that a real eval run justified stay, even if emphatic. The eval prompt and the
app prompt share the rules half, asserted in `tests/test_provider_chain.py`;
the app's asks for a Russian `why`.

## Speech recognition

`providers/asr.py` tries: **Workers AI** Whisper (`whisper-large-v3-turbo`,
language pinned to `et`) → OpenRouter audio → HF Whisper → local whisper.cpp
(TalTech verbatim) → local Voxtral. In production the Worker answers
`/api/transcribe` through its `AI` binding; the app then judges the transcript
(`/api/transcribe/text`). With nothing configured the speaking tab still
records and plays back.

## Other services

- **TTS** — TartuNLP (`providers/tts.py`), cached on disk.
- **Sentence translation** — TartuNLP (`providers/translate.py`), on request.
- **Dictionary** — Ekilex API (`providers/ekilex.py`) with `EKILEX_API_KEY`,
  else the Sõnaveeb mirror (`providers/sonapi.py`).
