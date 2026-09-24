# AI providers

## Production lanes

| Task | Engine | Boundary |
|---|---|---|
| Grammar explanations and tutor | Cloudflare Workers AI GPT-OSS-120B, then deterministic Vabamorf evidence | Models explain and assess open writing; code owns drill keys, mastery and FSRS (`docs/ai-boundaries.md`). |
| Speech recognition | Cloudflare Workers AI Whisper through the Worker | Transcript and feedback are advisory. The learner reviews recorded audio in `Hindamiskomplekt` before it can become ASR evaluation data (`docs/asr-evaluation.md`). |
| Estonian speech synthesis | TartuNLP Neurokõne | Valid complete WAV files are cached atomically; an uncached failure is visible. |
| Sentence translation | TartuNLP Neurotõlge | Translation supports reading and writing; it never grades an answer. |
| Word lookup | Ekilex with `EKILEX_API_KEY`, then the Sõnaveeb mirror | Dictionary answers retain their source. |

`providers/grammar.py` orders an **explicitly configured local trial** before
Workers AI and the deterministic fallback. The tutor uses the same qualified
LLM list. Deterministic spelling, agreement and rection findings take
precedence on conflicting spans. Mistral, NVIDIA, OpenRouter, public GEC and
Estonian-to-Estonian normalization are evaluation-only; they are not automatic
hosted fallbacks. Responses name the engine that answered. A malformed or empty
model response is never a correctness verdict.

Check the production lane with the `smoke` workflow and `deep: true`:
configuration alone proves only that a key is present. That smoke
does not measure explanation accuracy or learner ASR quality.

## Budgets and failures

Origin-side lanes have best-effort daily call allowances in snapshotted
`progress.db` (`providers/budget.py`). `/api/engines` reports these counts.
They are not hard billing caps: token and audio cost vary, account usage is
shared, concurrent checks can overlap, and recent snapshots can be lost. Worker
ASR uses Cloudflare's account quota instead of the Python budget.

The grammar and origin-side ASR chains share a persistent circuit breaker
(`providers/breaker.py`): skip a lane after two failures for 15 minutes, then
double the cooldown up to six days. Missing credentials skip a lane without
counting as a failure. Interactive grammar/tutor calls make one attempt per
lane; explicit evaluations may retry. Translation, TTS and Worker ASR are
single engines without that breaker. No production request depends on the
public GEC service.

## Candidate evaluation

The `hand` grammar track in `eesti/evals/gec.py` has ten planted errors and
eight clean controls. Their labels and EKI/Sõnaveeb evidence are in
[`evaluations/hand-set.md`](evaluations/hand-set.md). This is a diagnostic set,
not a native-speaker gold corpus. The evaluator distinguishes a no-op
replacement from a changed proposal, and both detection and clean-pass rates
matter. Review actual edits and Russian explanations before a lane change.
The separate `--track external` uses TalTech's corrected-sentence material
and reports recall by error class plus a clean-control rate. Prior candidate
measurements remain in `docs/evaluations/providers.json`; they do not authorize
automatic promotion. The weekly `eval.yml` checks the production grammar lane.
A green run with no measured cases is not a pass.

```bash
python -m eesti.cli eval --provider workers-ai
python -m eesti.cli eval --provider workers-ai --track external
python -m eesti.cli models --provider nvidia --limit 10
```

Model IDs can disappear. Check the live catalogue and the task-specific eval
before pinning a replacement. `deploy/set-llm-key.sh` can set a lane's
`<LANE>_MODEL` override on Cloud Run. The app and eval prompts share the rules
half; the app asks for a Russian explanation. Form existence alone cannot
validate an explanation's contextual grammar claim.

### Public GEC and dedicated correction models

The TartuNLP public GEC adapter is retained for bounded diagnostics, not
learner traffic. Its [OpenAPI contract](https://api.tartunlp.ai/grammar/openapi.json)
accepts `language` and `text`; an invalid JSON or schema response is a failure,
not “no corrections.” The service's availability, latency and linguistic quality
must all be rechecked before promotion:

```bash
python -m eesti.cli provider-health --timeout 5
python -m eesti.cli eval --provider tartunlp
```

The [TartuNLP GEC 8B](https://huggingface.co/tartuNLP/Llama-3.1-8B-est-gec-july-2025)
and its [Ollama wrapper](https://github.com/TartuNLP/gec-ollama-api) are
separate local correction experiments. The wrapper's licence does not relicense
the model weights. A corrected sentence alone is not a sourced Russian
explanation or a drop-in replacement for the app's JSON tutor prompt. No
always-on model host or laptop tunnel is part of production.

### Local EstLLM

[TartuNLP EstLLM 8B Instruct 1125](https://huggingface.co/tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125)
is an evaluation-only general tutor candidate. Model-card grammar benchmarks
measure a different task from learner correction and do not establish safe
Russian explanations. The downloaded GGUF stays in Ollama's local model store
outside this checkout, so `git pull` does not delete it. To repeat the
explicit trial, start Ollama and run:

```bash
LOCAL_LLM_URL=http://127.0.0.1:11434/v1 \
LOCAL_LLM_MODEL=hf.co/mradermacher/Llama-3.1-EstLLM-8B-Instruct-1125-GGUF:Q4_K_M \
python -m eesti.cli eval --provider local
```

Keep it out of learner traffic until it passes both the planted-error and
clean-sentence checks and its proposed edits are reviewed. English explanations
are acceptable in this labelled private trial; production explanations remain
Russian. EstNLTK/Vabamorf and EKI Sõnaveeb/Teatmik provide the form and rule
evidence; neither makes a model's contextual claim authoritative.

## Speech, TTS and translation

Production `/api/transcribe` uses the Worker's AI binding with Estonian pinned
and open-question context where appropriate, never the read-aloud target. The
origin's `providers/asr.py` retains local-development compatibility paths;
those are not production fallback recognisers. Compare any candidate only on
the same manually reviewed learner recordings, including false acceptance of
wrong forms (`docs/asr-evaluation.md`).

TTS uses the [Neurokõne contract](https://github.com/TartuNLP/text-to-speech-api)
with text, speaker and speed. Translation uses the
[Neurotõlge contract](https://github.com/TartuNLP/translation-api) with
three-letter language codes. Their health is independent of public GEC.
Credentials and placement are described in `docs/setup.md`.
