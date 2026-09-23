# ASR choice and evaluation

Production stays on Cloudflare Workers AI `@cf/openai/whisper-large-v3-turbo`.
The comparison reference is TalTech verbatim Whisper on the owner's machine.
This does not claim Cloudflare is more accurate: no manually verified learner
corpus is available in this checkout, so quality and comparative latency are
**unmeasured on learner speech**. Native-speech runtime controls below establish
that the local options actually execute, not that they improve learner grading.
No second production recogniser is justified yet (ADR-0005).

## Current options

Model cards, file sizes and Hugging Face `inferenceProviderMapping` were read
live on 2026-09-22. Sizes below are decimal GB/MB of weights, **not measured
peak RAM**. The five TalTech checkpoints expose empty provider mappings; that
means no provider is listed by HF, not proof that no private host exists.

| Model | Licence; released files | Runtime / streaming | Fit here |
|---|---|---|---|
| [TalTech Whisper verbatim 2604](https://huggingface.co/TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604) | MIT; 809M parameters, 3.24 GB FP32, official GGML 1.62 GB and CT2 1.62 GB | Transformers, whisper.cpp (CPU/Metal/CUDA), faster-whisper/CTranslate2 (CPU int8/CUDA); utterance decoding, not native causal streaming | Best first reference by compatibility and operating cost; learner false acceptance is unmeasured. Training includes manually transcribed speech and model-transcribed broadcast/English speech, so “verbatim” is not a guarantee. |
| [Zipformer et-en](https://huggingface.co/TalTechNLP/streaming-zipformer.et-en) | MIT; encoder 261 MB FP32 or 70 MB int8, plus small decoder/joiner | sherpa-onnx CPU; genuine streaming; card links a browser application | Smallest plausible private/mobile experiment. Broadcast training and pseudo-labels do not establish morphology fidelity on L2 speech. No hosted API contract established. |
| [Zipformer large et-en](https://huggingface.co/TalTechNLP/streaming-zipformer-large.et-en) | MIT; encoder 593 MB or 155 MB int8, plus decoder/joiner | sherpa-onnx CPU streaming | Feasible on an ordinary machine, but quality/latency against the smaller model needs measurement. No current need for live captions. |
| [Voxtral Mini 3B Estonian](https://huggingface.co/TalTechNLP/Voxtral-Mini-3B-2507-estonian) | Apache-2.0; 4.68B total parameters including audio, 9.36 GB BF16 Transformers shards | Transformers CUDA example; existing optional llama.cpp/GGUF path uses third-party conversion, not these official weights; no causal streaming claim | Instruction-dependent transcription, summaries and other tasks; more scope to normalise. Runtime support/quantisation needs separate validation. Not a CTranslate2 Whisper model. |
| [Voxtral Mini 4B Realtime 2609](https://huggingface.co/TalTechNLP/Voxtral-Mini-4B-Realtime-estonian-2609) | Apache-2.0; 4.43B parameters, 8.86 GB BF16 per layout | Official vLLM `/v1/realtime` WebSocket; Transformers ≥5.2; card suggests 480 ms delay, not measured end-to-end latency here | Card reports 6.8% internal benchmark WER, not learner fidelity. GPU-oriented deployment and session complexity buy a feature current speaking flows do not need. Do not use the older Voxtral llama.cpp adapter for it. |
| [Cloudflare Whisper turbo](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/) | Hosted OpenAI Whisper; upstream MIT weights, hosted service terms also apply | Existing Worker AI binding; record-and-submit, `language=et`, optional open-answer question context, never the read-aloud target | No model RAM/cold-load operation on our origin. Audio leaves device; graceful refusal/playback on failure. Actual learner quality still needs the same corpus. |

For planning, allow several GB of RAM for Whisper beyond its 1.62 GB file, and
measure CPU int8/Metal on the actual laptop. Zipformer weights suggest a smaller
footprint, but decoder state, runtime and browser copies add memory. BF16 Voxtral
requires **more than** its 8.9–9.4 GB weight footprint in RAM/VRAM; 16–24 GB GPU
capacity is a sensible trial budget, not a published minimum or a measurement.
Training GPU counts are not inference requirements.

The official [faster-whisper implementation](https://github.com/SYSTRAN/faster-whisper)
supports CPU int8 and local CT2 models; its published timings use other models
and hardware and cannot predict this learner's latency. It does not execute
Zipformer or Voxtral. The April TalTech card ships CT2 and GGML already, so there
is no need to invent a converter. Reference revisions: Whisper `310c5509`,
Zipformer `7edbacc1`, large `2812262b`, Voxtral 3B `bb6489cf`, realtime `e50b2a54`.

TalTech also ships complete applications. [Jutukuva](https://github.com/TalTechNLP/jutukuva)
uses local sherpa-onnx and offers Apple Silicon, Intel, Windows and Linux builds.
Its [recogniser configuration](https://github.com/TalTechNLP/jutukuva/blob/master/electron/asr/sherpa-config.js)
downloads a different checkpoint:
[Zipformer large **w2n**](https://huggingface.co/TalTechNLP/streaming-zipformer-large.et-en.w2n)
(Apache-2.0), trained to turn spoken numbers into digits. The card warns about
numbers longer than four digits. This is useful captioning software, but its
number normalisation would hide distinctions in this app's speaking exercises;
do not silently substitute it for the plain verbatim reference. Its optional
shared sessions also differ from purely local inference.
[est-asr-backend](https://github.com/TalTechNLP/est-asr-backend) is a self-hosted
Deno/SQLite upload-and-progress API over the Nextflow transcription pipeline,
with optional speaker identification and punctuation. Neither application
establishes a supported hosted short-answer API for this app. Reusing a model
and the existing evaluation harness has less operational cost than adopting
either application's separate UI, queues and persistence.

[Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
lists 46.63 neurons per audio minute (about $0.0005), sharing the free 10,000
neurons/day with text inference. Ten minutes uses about 466 neurons. The free
plan rejects work above its allowance; Python's call counters do not meter
Worker ASR or guarantee an account-wide budget. A self-hosted GPU is not free:
[Cloud Run L4](https://docs.cloud.google.com/run/docs/configuring/services/gpu)
requires at least 4 CPU/16 GiB and GPU billing. Notebook/Space demos can sleep,
have queues and lack a production SLA; no usable free always-on GPU is configured
for this app. Local reference runs cost the owner's hardware/time but add no
production service.

## Executed runtime controls

Three existing EKI Külli corpus WAVs (3.83, 4.85 and 8.32 seconds) were run
through the real reference adapter, a separate sherpa-onnx trial, and the
production-model Cloudflare REST adapter with no question/answer prompt.
These are native narration, **not learner recordings**. Their supplied text
was not manually verified here; none was sealed into the learner benchmark.

| Runtime | Observed seconds for the three clips | Local process peak RSS |
|---|---|---|
| Cloudflare Whisper turbo REST | 2.09 / 5.93 / 2.03 | Hosted; not measured |
| TalTech Whisper CT2, CPU int8, beam 5, temperature 0 | 11.34 cold / 4.48 / 4.62; first clip repeated warm: 4.43 | 2.31 GB |
| TalTech small Zipformer int8, sherpa-onnx, 2 CPU threads | 0.079 / 0.099 / 0.161, plus 0.726 load | 0.30 GB |

Local hardware was Apple M5 with 32 GiB RAM, Python 3.14, faster-whisper 1.2.1,
CTranslate2 4.8.2 and sherpa-onnx 1.13.8. CT2 cold time includes artifact hashing
and model loading. Zipformer used modified beam search, sample-rate conversion
and 0.66 seconds of tail padding; file decoding speed is not live endpoint
latency. Each engine returned text for all three controls. The compound
`enesestmõistetav` was joined by both TalTech models and split by Cloudflare;
all three diverged substantially on the unusual names in the third clip.
That is a useful challenge case, not a reliable accuracy ranking.

The CPU paths are feasible locally. These timings do not predict Cloud Run
performance, L2 morphology fidelity, false acceptance or mobile battery cost.
Whisper remains the implemented comparison engine; the smaller Zipformer trial
supports keeping it as a possible future local/streaming reference, with no
additional production service or automatic fallback. The next quality test is
the verified learner workflow below, with numbers and common names included.

## TartuNLP speech is separate from GEC, translation and TTS

The official [ASR API](https://github.com/TartuNLP/speech-to-text-api) is an
asynchronous job service with temporary audio storage, RabbitMQ and MySQL;
its [CPU worker](https://github.com/TartuNLP/speech-to-text-worker) is based on
Kiirkirjutaja. This is not the grammar endpoint or Neurotõlge. No current public
short-answer inference contract or operational ASR result was established here;
we did not submit private audio. Self-hosting that stack adds three services.
[TartuNLP's whisper_streaming fork](https://github.com/TartuNLP/whisper_streaming)
is inference infrastructure, not evidence of a hosted Estonian recogniser.

[Whisper large-v2 et-children](https://huggingface.co/tartuNLP/whisper-large-v2-et-children)
(Apache-2.0, 6.17 GB FP32) and
[XLS-R 300M et-children](https://huggingface.co/tartuNLP/xls-r-300m-et-children)
(CC BY 4.0, 1.26 GB) are downloadable Transformers models for children's speech.
Their validation results do not establish an advantage on this adult Russian-L1
learner; they are not preferable first references to the smaller current TalTech
Whisper. These are distinct from TartuNLP's text-to-speech voices.

## Smallest trustworthy corpus workflow

1. Under `cli serve`, record in `Rääkimine → Hindamiskomplekt`. Choose `Loe
   ette` for a read-aloud sentence (including occasional planted errors) or
   `Vasta küsimusele` for an open answer. The app saves audio locally, the
   **displayed read-aloud prompt** in `.txt` or an empty `.txt` for an open
   answer, and the actual question in `.question`. If ASR is configured, it
   also shows and saves its tentative guess in a separate JSON draft; this request
   sends audio to the configured recognition service. Neither prompt nor ASR
   output is ground truth without listening.
2. Listen to each clip and edit its `.txt` to exactly what was audibly spoken,
   including mistakes and hesitations. Exclude ambiguous clips; an uncertain
   acoustic distinction is not a gold label. Use the same written-number policy
   for both engines; the normaliser deliberately does not turn numbers or names
   into a model-specific canonical spelling.
3. Seal the review with `asr-verify --listened`. Token indices are zero-based,
   after Unicode NFC, case folding and punctuation removal. For a recording
   actually saying “Ma ostsin uus auto”, use:

   ```bash
   python -m eesti.cli asr-verify data/eval/asr/0000.webm --listened \
     --planted-index 2 --accepted uue --focus 2 --tag morphology
   ```

   `--accepted` is the expected form that would hide the error. `--focus` may be
   repeated for morphology-sensitive words; tag clips `numbers`, `names`,
   `short-answer`, `hesitation`, `noise` as appropriate. Normal clips need only
   `--listened` and optional focus/tags. An adjacent `.question` is loaded
   automatically and sealed as context; an explicit `--question` must match it.
   Hashes bind review to audio and text;
   changing either requires listening and verification again.
4. Start with 20 verified clips, at least five planted-error probes and five
   morphology tokens, covering correct controls, learner forms, numbers, common
   names/vocabulary and hesitations. Expand toward 80–150 clips over different
   sessions before a provider decision. These are pilot floors, not confidence
   guarantees or proof of accent/pronunciation competence.
5. Install optional `faster-whisper` in a local evaluation environment and
   download the official model's **ct2 subdirectory** at the revision above
   using Hugging Face's download tooling. Set `ASR_REFERENCE_MODEL` to that
   local directory (not a secret). No model is downloaded implicitly and no
   extra runtime goes into `requirements.txt` or the Cloud Run image. Existing
   whisper.cpp is also usable with its official GGML weights and WAV input;
   convert browser WebM/MP4 to mono 16 kHz PCM with ffmpeg first, then verify
   that converted clip. The CT2 path decodes browser audio through PyAV.
6. Run the existing harness, with Cloudflare credentials only in the ignored
   `.env`. This explicitly sends the verified audio to Cloudflare; the reference
   runs locally. The REST request uses the production model/options. Read-aloud
   controls have no hint. For open answers, supply the **actual question** with
   `asr-verify --question "Kus te elate?"`; it travels in the sealed annotation
   and reaches Cloudflare's `initial_prompt`, matching that production flow.
   Never put the target answer/transcript there. Compare hinted and unhinted
   corpora separately: context can bias recognition. The local CT2 reference
   intentionally ignores question hints. Timings exclude the Worker's origin hop.

   ```bash
   python -m eesti.cli eval --suite asr --engine workers-ai \
     --engine faster-whisper --output data/eval/asr-results.json
   ```

Results include corpus-weighted WER and CER, edit counts, per-clip transcripts,
actual engine/model fingerprint, failure coverage, p50/p95/max latency,
aligned false-accept count/rate and morphology-token error rate. A deletion or
unrelated substitution is an error but is **not** a repaired expected form.
The paired bootstrap reports mean per-clip WER difference (a distinct statistic
from corpus WER), pairs audio/annotation hashes, and refuses a decisive result
on incomplete or undersized evidence. Read the tagged details for numbers and
names; a generic WER can hide regressions there. Reference cold model loading
is included in the first clip; distinguish it from warm latency.
The CT2 reference fixes temperature to zero: faster-whisper's default sequence
of fallback temperatures would otherwise introduce sampling on difficult clips.
Its identity includes runtime versions and hashes of weights, tokenizer and
configuration, because a tokenizer change can alter results without changing
the weights. No target answer or question is supplied to this reference.

Exit 2 means insufficient/unavailable evidence, including an empty corpus.
`chain` remains diagnostic only and cannot support a provider decision. Reports
contain personal transcripts: keep them under ignored `data/eval`, not in PRs
or public workflow artifacts. Commit only anonymous aggregates after review.
A production change needs lower false acceptance without unacceptable WER/CER,
morphology or latency regressions, with failures and hosting costs accounted
for. No result automatically switches providers.
