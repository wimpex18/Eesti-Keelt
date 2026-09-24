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

`providers/grammar.py` builds: explicitly configured **local trial** →
**Workers AI GPT-OSS-120B** → **Vabamorf offline**. The tutor uses the same
qualified LLM list. Deterministic spelling, agreement and rection accompany
successful model answers and take precedence on conflicting spans.

Public GEC is removed from automatic requests because it is unavailable.
Neurotõlge remains the healthy translation service, but est→est normalization
is evaluation-only: low-recall normalization must not stand in for a grammar
verdict. Mistral, NVIDIA and OpenRouter clients remain explicit evaluation
candidates, not automatic fallbacks. A Cloudflare outage now produces visible
deterministic offline evidence instead of trying a known unsuitable checker.
No additional production host, paid plan or model-specific routing chain is added.

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

`PROVIDER_TIMEOUT=5` bounds the retained diagnostic adapter: the implementation gives
each endpoint a 2.5-second socket timeout, plus connection overhead. It is not a
strict total wall-clock deadline or evidence that a healthy service fits it.
Automatic learner requests never call this service. Keep diagnostics bounded. Re-evaluate successful latency and grammar quality before promotion.
An invalid JSON/schema response is a failure, never “no corrections”.

```bash
python -m eesti.cli provider-health --timeout 5
python -m eesti.cli provider-health --timeout 70  # six bounded POSTs; operator diagnostic
python -m eesti.cli eval --provider tartunlp     # quality, distinct from health
```

The diagnostic prints per-endpoint status/failure, latency and timestamp, uses
canned text and never prints remote error bodies. Exit 2 means not operational.
It can be run in the local or Cloud Run project runtime; the direct probes above
were local. Production smoke with `deep: true` separately demonstrated an answering
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

LLM clients (`providers/llm.py`, OpenAI-compatible), checked 2026-09-23:

| Candidate | Planted errors caught | Correct sentences left alone | Failed calls | Median / max seconds |
|---|---|---|---|---|
| **Workers AI GPT-OSS-120B — production** | 8/10 | 8/8 | 0 | 4.03 / 9.01 |
| Mistral Large latest | 2/10 | 8/8 | 0 | 3.43 / 5.38 |
| Mistral Medium 3.5 (`mistral-medium-3-5`) | 3/10 | 7/8 | 0 | 3.49 / 4.22 |
| Workers AI Qwen 3.8 27B, default settings | 7/8 measured | 7/7 measured | 3 | 5.83 / 30.23 |
| Qwen 3.8, low reasoning / 2,000 completion tokens | 7/9 measured | 8/8 | 1 | 6.40 / 25.07 |
| Workers AI Gemma 4 26B A4B | 6/7 measured | 6/6 measured | 5; quality score invalid | 21.51 / 30.06 |

Exact reports: `docs/evaluations/providers.json`. These use the existing 18-case
**error-detection** eval; “caught” does not certify every proposed replacement
or Russian explanation. No raw learner text is in the reports. Calls used one
attempt, a 30-second socket timeout (25 for Qwen low); timing includes client
pacing, network and inference. Clean controls and failure coverage matter as
much as recall. Qwen's second trial used the documented `reasoning_effort=low`
and `max_completion_tokens=2000`, so its slower/failed calls are not merely an
untested default-parameter objection.

All tested IDs were present in live authenticated catalogues. Cloudflare's
GLM 5.3 Flash is also present but marked `require_workers_paid=true`; it was
not promoted or invoked on an assumed free plan. Current official references:
[Qwen 3.8](https://developers.cloudflare.com/workers-ai/models/qwen3.8-27b/),
[Mistral Medium 3.5](https://docs.mistral.ai/models/mistral-medium-3-5-26-04),
and [Cloudflare model catalogue](https://developers.cloudflare.com/ai/models/).

**Decision:** keep GPT-OSS-120B, remove weak hosted fallbacks from automatic
routing. Mistral is reachable but inaccurate on this task, not “unstable”. Its
newer model did not fix that. Qwen and Gemma did not show a reliable latency/
quality advantage. NVIDIA's [18/18 timeout result](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35721653153)
and OpenRouter's [partial/low-recall result](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35602506211)
also do not justify automatic use. Configuring `LOCAL_LLM_URL` remains an explicit
private trial; no local server is part of production.

The [latest deep production smoke before PR #67](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35910679079)
reached Workers AI and verified Access/origin protection, Ekilex and reference
data. It tested the deployed `main`, not pending exam-file resolution or
microphone recognition.

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

Current Estonian-language research (2026-09-23), including the
[EstLLM paper](https://huggingface.co/papers/2603.02041):

| Resource | Fit for this app |
|---|---|
| [TartuNLP/TalTechNLP EstLLM 8B Instruct 1125](https://huggingface.co/tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125) | Best small *general* local grammar/tutor trial. Its published Grammar-et score is 0.831, but that is multiple-choice competence, not learner correction or Russian explanations. Llama 3.1 terms; 4,096-token recommended context and imperfect multi-turn support. |
| [Apertus EstLLM 8B Instruct 0326](https://huggingface.co/tartuNLP/Apertus-EstLLM-8B-Instruct-0326) | Apache-2.0 alternative; published Grammar-et 0.713. Trial only if licence simplicity matters or our own eval warrants it. |
| [EstLLM 70B Instruct 0826](https://huggingface.co/tartuNLP/Llama-3.1-EstLLM-70B-Instruct-0826) | Newer large research model; impractical as a laptop-local lane on the owner's 32 GB Mac. No production hosting budget or task eval. |
| [TartuNLP Estonian GEC 8B](https://huggingface.co/tartuNLP/Llama-3.1-8B-est-gec-july-2025) and [its Ollama wrapper](https://github.com/TartuNLP/gec-ollama-api) | Dedicated corrected-sentence model. Requires a separate adapter and licence check; the model card has incomplete licence metadata. A corrected sentence alone cannot supply the app's sourced Russian explanation. |
| [TalTech grammar_et](https://huggingface.co/datasets/TalTechNLP/grammar_et) and [inflection_et](https://huggingface.co/datasets/TalTechNLP/inflection_et) | Local evaluation controls, not an answer key or licensed app content. |
| [EstNLTK/Vabamorf](https://github.com/estnltk/estnltk), [EKI Sõnaveeb/ÕS 2025](https://teatmik.eki.ee/teatmik/sonaveebi-kasutajale/) and [EKI Teatmik](https://eki.ee/teatmik/) | Deterministic forms, live lexicography and current rule references. The app already uses Vabamorf, Ekilex/Sõnaveeb and linked EKK; these resources complement a model, rather than making model output authoritative. |

The [TalTechNLP model catalogue](https://huggingface.co/TalTechNLP/models)
also has newer Estonian ASR and translation models. They are different tasks:
compare ASR only on manually verified learner recordings, and compare
translation with the working Neurotõlge route before changing either.

For a private trial, run an OpenAI-compatible server such as Ollama and set
`LOCAL_LLM_URL` and `LOCAL_LLM_MODEL` in that process only. A local URL does not
make the owner's laptop an always-on production service. Apply the app's
error-detection and clean-sentence eval before trusting a local model. No
public tunnel or automatic routing change is justified by model-card scores.
The downloaded GGUF is in Ollama's local model store (`~/.ollama/models` on
this Mac, with no `OLLAMA_MODELS` override), outside this Git checkout;
`git pull` cannot remove it. `ollama list` confirms it remains installed.
To repeat the explicit trial, run:

```bash
LOCAL_LLM_URL=http://127.0.0.1:11434/v1 \
LOCAL_LLM_MODEL=hf.co/mradermacher/Llama-3.1-EstLLM-8B-Instruct-1125-GGUF:Q4_K_M \
python -m eesti.cli eval --provider local
```

The owner's Mac ran the 4.9 GB third-party `Q4_K_M` GGUF of EstLLM 8B 1125
through Ollama 0.34.3 and the app's unmodified 18-case prompt on 2026-09-23.
All 18 calls returned parseable JSON. The first detection-only run flagged
**10/10** planted errors, but its scorer also counted unchanged replacements.
After excluding no-op edits, the repeat caught **9/10** and left **0/8** clean
controls alone. On that repeat,
six outputs were no-op replacements and two proposed edits; one wrongly changed
`võtmeid` to `võtme` after negation. It also proposed edits for two of three
short, clean examples taken from [EKI's object-case rule](https://eki.ee/teatmik/osasihitis-ja-taissihitis/).
These are distinct failures: a no-op is invalid correction output, while an
incorrect edit is a linguistic error. The hand-set labels and sources are
[auditable](evaluations/hand-set.md); it is a diagnostic set, not a native-speaker
gold corpus. An English-explanation/few-shot variant found 8/10 planted errors
and left 6/8 clean controls alone when identical replacements were discarded;
it remains below the release gate. Keep this quantization out of learner traffic.
English is acceptable for an explicit local trial; Russian remains preferable
for the target learner and required in the production UI.

## Choosing a model: the eval

Two tracks, both with a precision half, because a checker that flags every
partitive teaches the wrong rule:

- **`hand`** (default) — `eesti/evals/gec.py`, 18 Estonian sentences written
  for this app's weakness: 10 with a planted error (**recall**) and 8 already
  correct (**clean pass rate**, named `precision` in the CLI). The report now
  distinguishes no-op responses from actual edits. [Labels and EKI/Sõnaveeb
  sources](evaluations/hand-set.md). Exits non-zero below 0.8 on either score; exit 2
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
model. It runs weekly on Workers AI, the production grammar lane. The model menu may contain only
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

- **TTS** — retain TartuNLP Neurokõne (`providers/tts.py`). Actual synthesis
  of three short Estonian sentences succeeds: HTTP 200, mono 22,050 Hz
  IEEE-float WAV. This is a separate service from GEC. The
  [official contract](https://github.com/TartuNLP/text-to-speech-api) takes
  text, speaker and speed; the default `mari` voice remains available.
  Both downloads and cached files must contain complete WAV data; error JSON
  and truncated audio are rejected, and cache writes are atomic. Valid cached
  audio remains usable during an outage; an uncached failure returns a visible
  503 instead of an unplayable file. The public service has no verified SLA.
- **Sentence translation** — retain TartuNLP Neurotõlge
  (`providers/translate.py`). Real Estonian→Russian and Estonian→English
  requests succeed for all three test sentences within the existing five-second
  budget. The
  [official request schema](https://github.com/TartuNLP/translation-api)
  accepts three-letter language codes and an optional `application` field in
  the JSON body; no client credential is needed for the tested public route.
  Only nonempty strings or lists of such strings count as translations.
  Malformed responses remain unavailable, never displayed as dictionary or
  number representations. Translation supports reading and writing checks,
  never grades learner evidence. Public translation success does not establish
  GEC availability or linguistic authority.
- **Dictionary** — Ekilex API (`providers/ekilex.py`) with `EKILEX_API_KEY`,
  else the Sõnaveeb mirror (`providers/sonapi.py`).
