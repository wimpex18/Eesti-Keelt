# AI providers

Origin-side lanes have best-effort daily call allowances (`providers/budget.py`)
in snapshotted `progress.db`. `/api/engines` reports those counts. They are not
hard billing caps: token/audio cost varies, provider accounts share usage,
concurrent checks can overlap, and a crash can lose recent snapshot counts.
Worker ASR does not pass through this Python budget. Cloudflare's account quota
is the production speech limit.

Grammar checks and origin-side speech recognition go through a chain of
interchangeable providers with a shared circuit breaker (`providers/breaker.py`:
skip a lane after 2 failures for 15 min, doubling up to 6 days, persisted in
`progress.db`). Translation, TTS and the Worker's speech recognition are single
engines without a breaker. Missing keys are skipped, not failures. Responses
name the engine that answered.

## Grammar chain

`providers/grammar.py` builds: **LLM lanes** in `LLM_PREFERENCE` →
**TartuNLP GEC** → **Neurotõlge est→est** → **Vabamorf offline**.
Deterministic spelling, agreement and rection findings accompany every successful
answer and take precedence on conflicting spans. Fluency is not authority.

- GEC remains a public, optional correction fallback. Putting its unavailable
  backend ahead of a working explaining lane costs latency without evidence of
  better learner feedback. Both endpoint failures appear in diagnostics.
- Neurotõlge (`tartunlp-mt`) is a **translation** service used as a conservative
  est→est fallback. Only same-lemma substitutions survive; aspect changes are
  not established by its normalisation. It explains nothing. Its existing
  18-case eval is low recall, so it cannot replace an explaining model.
- Public TartuNLP text services may retain submitted text under their terms;
  do not infer GEC privacy or availability from translation/TTS availability.

### Public GEC: observed service and contract

Direct probes from this checkout's Python 3.14 runtime on **2026-09-22** used
`POST {"language":"et","text":...}` with `Content-Type: application/json`.
The sentences were “Ma elan Tallinnas.”, “Mul on kaks koer ja üks kass.” and
“Ma lugesin raamatut läbi.” Both endpoints timed out on all three at a 12-second
read deadline. A longer probe of the first sentence with a 70-second deadline
and `application: eesti-keelt` returned **HTTP 500 after 60.143 s on `/grammar/v2`
and 60.164 s on `/grammar/`**. These are observed failures, not an assumed
latency requirement.

The [live OpenAPI](https://api.tartunlp.ai/grammar/openapi.json) returns 200,
still defines the same `language`/`text` body (text ≤10,000 characters), and
specifies no client authentication or application header. Missing `text`
returns 422 immediately. The official
[grammar API](https://github.com/TartuNLP/grammar-api) documents credentials
for its **upstream model endpoints**, not for our public client. Thus no schema
or client credential mismatch was found. An application header did not cure
the failure; backend logs were not available, so the internal cause is unknown.
The public deployment's model identity was not verified from its responses.

`PROVIDER_TIMEOUT=5` is an interactive fallback budget: the implementation gives
each endpoint a 2.5-second socket timeout, plus connection overhead. It is not a
strict total wall-clock deadline or evidence that a healthy service fits it.
Keep this bound while the service is unusable; do not raise learner waits to
60 seconds. Re-evaluate successful latency and grammar quality before promotion.
An invalid JSON/schema response is a failure, never “no corrections”.

```bash
python -m eesti.cli provider-health --timeout 5
python -m eesti.cli provider-health --timeout 70  # six bounded POSTs; operator diagnostic
python -m eesti.cli eval --provider tartunlp     # quality, distinct from health
```

The diagnostic prints per-endpoint status/failure, latency and timestamp, uses
canned text and never prints remote error bodies. Exit 2 means not operational.
It can be run in the local or Cloud Run project runtime; the direct probes above
were local. Production `smoke -- deep:true` separately demonstrated an answering
Workers AI grammar lane, not GEC health or ASR accuracy.

### Self-hosted TartuNLP GEC

The official [gec-ollama-api](https://github.com/TartuNLP/gec-ollama-api) provides
CPU/GPU Docker instructions and GGUF conversion/quantisation for
[tartuNLP/Llama-3.1-8B-est-gec-july-2025](https://huggingface.co/tartuNLP/Llama-3.1-8B-est-gec-july-2025).
The released weights are 8.03B BF16 parameters, about **16.06 GB**, before runtime
and KV-cache memory. FP16/BF16 needs more memory than that footprint; budget
24–32 GB RAM/VRAM for a trial. Q4 weights have a roughly 4 GB theoretical payload
plus quantisation metadata; plan roughly 6–10 GB resident memory and measure.
These are sizing estimates, not measured requirements or latency results.

CPU execution is useful for private experiments on an existing machine, but
interactive cold-load/token latency is unmeasured. GPU hosting adds paid compute,
authentication, model storage, health checks and operations. The wrapper's MIT
licence does not relicense the Llama-derived weights: the model card's licence
metadata is incomplete; upstream Llama terms also need review before hosting.
The checked Compose file defines GPU profiles, despite the README's CPU command;
use its `Dockerfile.cpu` instructions for a local trial, not an assumed working
CPU Compose deployment. Reproducing the public v2 explanation stack may need
GED/GEE models and the grammar middleware, not just the GEC model server.

**Decision:** no self-hosted production GEC or laptop tunnel. No free always-on
GPU is configured and no measured correction/latency win offsets the additional
service. A corrected-sentence model is not a drop-in for the existing JSON
teacher prompt. Test it separately if local privacy becomes the deciding need.

LLM lanes (`providers/llm.py`, OpenAI-compatible):

| Automatic order | Lane | Default model | Current evidence |
|---|---|---|---|
| 1, only when explicitly configured | `local` | EstLLM 8B GGUF via Ollama | Private local trial; no learner-task quality measurement |
| 2 | `workers-ai` | `@cf/openai/gpt-oss-120b` | 9/10 planted errors caught, 8/8 clean sentences unflagged, 0 broken calls |
| 3 | `mistral` | `mistral-large-latest` | 2/10 caught, 8/8 clean, 0 broken; conservative but low recall |
| 4 | `openrouter` | `dots-studio/dots-3-note-preview:free` | 4/8 measured errors caught, 7/8 clean, 2 broken calls |
| Explicit eval only | `nvidia` | `z-ai/glm-5.3-flash` | All 18 cases failed with `TimeoutError`; no quality score |

These are the app's small hand-written grammar eval, not general linguistic
accuracy: [Workers AI](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35721650207),
[Mistral](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35721656195) and
[NVIDIA](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35721653153) on
2026-09-22; [OpenRouter](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35602506211)
on 2026-09-21. The three freshly checked default IDs were present in their
catalogues. NVIDIA's completion endpoint still timed out; catalogue presence
is not service health. It is excluded from automatic grammar **and tutor**
routing until it answers and passes a fresh evaluation.

Workers AI stays first among hosted lanes. Mistral precedes OpenRouter because
it left the correct sentences alone in this small test; both remain limited
fallbacks, and their suggestions never become code grading. Configuring a local
URL explicitly opts into local inference before hosted providers; it is not a
claim that EstLLM has won the evaluation. A production smoke reached Workers AI
in roughly 25 seconds for the complete grammar request; per-model latency was
not measured by these quality reports.

Interactive grammar/tutor requests use one completion attempt per lane, with
the existing 60-second socket timeout; explicit evals retain retries. These are
not a total request deadline. Tutor transport/JSON failures now update the same
persistent breaker as grammar. Task-specific grounding still decides whether
an answering model's content is usable.

Cloudflare has a shared 10,000-Neuron daily free allowance; Mistral's current
[Free mode limits](https://docs.mistral.ai/admin/billing-usage/usage-limits)
are organization/model-specific, not a guaranteed billion tokens. OpenRouter's
[free routes](https://openrouter.zendesk.com/hc/en-us/articles/39501163636379-OpenRouter-Rate-Limits-What-You-Need-to-Know)
allow 50 requests/day, or 1,000 after qualifying credit purchase, at 20/minute.
Actual account balances were not inspected. Local inference consumes the owner's
hardware; the NVIDIA evaluation endpoint has account limits and no verified
availability guarantee. Keys remain documented in `docs/setup.md`.

Override a pinned model without a deploy: set `<LANE>_MODEL` (e.g.
`WORKERS_AI_MODEL`, `LOCAL_LLM_MODEL`) on Cloud Run with
`deploy/set-llm-key.sh`.

### Local EstLLM

Run an OpenAI-compatible server (e.g. Ollama with the GGUF above) and set
`LOCAL_LLM_URL`. Local trials use the existing machine; no public tunnel is part of the chosen
architecture. Local inference has hardware costs and availability limits.
A self-hosted corrected-sentence GEC needs its own adapter/eval, not this prompt.

## Choosing a model: the eval

Two tracks, both with a precision half, because a checker that flags every
partitive teaches the wrong rule:

- **`hand`** (default) — `eesti/evals/gec.py`, 18 Estonian sentences written
  for this app's weakness: 10 with a planted error (**recall**) and 8 already
  correct (**precision**). Exits non-zero below 0.8 on either score; exit 2
  means nothing was measured.
- **`--track external`** — `eesti/evals/external.py`, TalTech's `grammar_et`:
  attested error/correction pairs, sampled. Recall is reported **per error
  class** (object case, locative, number, verb form, spelling, other), decided
  by morphology rather than by a hand-written label, and precision is measured
  on the dataset's own corrected sentences. Exits 1 below 0.5 recall or 0.8
  precision.

Both tracks score any lane, including the non-LLM ones
(`--provider tartunlp`, `--provider tartunlp-mt`).

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

Production is **Cloudflare only**, with a local TalTech evaluation reference
(`docs/asr-evaluation.md`). Hosted fallbacks below are local-development
compatibility paths, not a second production recogniser.


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
