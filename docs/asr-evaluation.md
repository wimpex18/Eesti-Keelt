# ASR choice and evaluation

Production uses Cloudflare Workers AI `@cf/openai/whisper-large-v3-turbo`.
[TalTech verbatim Whisper](https://huggingface.co/TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604)
is the local comparison reference. Native EKI narration has shown that TalTech
Whisper and Zipformer can run on the owner's machine; it has not measured their
accuracy on learner speech. No verified learner corpus is available in this
checkout, so there is no paired WER or false-accept result supporting a switch
(ADR-0003 and ADR-0005).

## Candidates and constraints

| Option | Role in this app |
|---|---|
| [Cloudflare Whisper turbo](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/) | Production record-and-submit ASR through the existing Worker. Audio leaves the device. |
| [TalTech Whisper verbatim](https://huggingface.co/TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604) | Local paired reference via its official CTranslate2 checkpoint and `faster-whisper`; its name does not guarantee preservation of learner errors. |
| [TalTech streaming Zipformer](https://huggingface.co/TalTechNLP/streaming-zipformer.et-en) | Possible small local or live-caption trial if partial transcripts become useful. It is not the current comparison engine. |
| [TalTech Voxtral Mini Estonian](https://huggingface.co/TalTechNLP/Voxtral-Mini-3B-2507-estonian) | Larger instruction-following speech model; requires a separate runtime and error-preservation evaluation. |
| [TalTech Voxtral Realtime](https://huggingface.co/TalTechNLP/Voxtral-Mini-4B-Realtime-estonian-2609) | 3 Sep 2026, Apache-2.0, 4B parameters in BF16 (8.9 GB), 6.8% WER on the Kõnetõlke benchmark (native broadcast speech, not learners). Streaming needs vLLM on a CUDA GPU; Transformers ≥ 5.2 transcribes whole files. No hosted endpoint (Workers AI offers none) and no MLX or GGUF build of the Estonian weights yet, so it cannot serve the phone app. Its role is a local paired candidate once `Hindamiskomplekt` holds verified clips; short exercises stay record-and-submit. |

[TartuNLP's ASR API](https://github.com/TartuNLP/speech-to-text-api) is an
asynchronous job stack rather than an established hosted short-answer endpoint
for this app. Its children's speech models target a different population. TTS,
translation, grammar GEC and ASR are separate services. Model-card scores,
public native-speech WER and runtime feasibility cannot substitute for a
paired test on this learner's voice. Any local reference runs on the owner's
hardware; no additional production inference host is configured.

## A ready-made benchmark

`python -m eesti.cli asr-bench` writes `data/eval/asr-bench/`: 20 EKI
*kõnekorpus* sentences read by native speakers (EKI's text is the truth), and
16 TartuNLP-synthesised learner sentences, 12 with one planted error each
(`Ma ostsin uus auto`, the recogniser must not hand back *uue*) and 4 correct
controls (`eesti/evals/asr_bench.py`). Truth is known by construction, so the
seal carries `provenance` instead of a listening confirmation. It ranks engines
on mishearing and on silent correction before any learner clip exists; it is
not a learner's voice.

`--engine voxtral-rt` runs TalTech's Voxtral Realtime through Transformers on
the owner's machine (`eesti/evals/asr_voxtral.py`, `VOXTRAL_RT_MODEL`); it is an
eval engine only, never in the production chain.

| Engine (26 Sep 2026) | Bench WER | Bench CER | Owner's 8 clips WER | Planted errors "fixed" (bench + owner) | Median latency |
|---|---|---|---|---|---|
| Workers AI Whisper turbo (production) | 20.0% | 3.6% | 36.4% | 0 of 15 | 2.8 s (hosted) |
| TalTech Whisper et-verbatim (`faster-whisper`, CPU int8, beam 5) | 5.7% | 0.7% | 7.3% | 2 of 15 | 4.4 s on 4 M5 threads; the home service on an Intel Mac |
| TalTech Voxtral Realtime (`voxtral-rt`, Apple M5, MPS, BF16) | 6.5% | 1.0% | 7.3% | 1 of 15 (`vastus` → *vastust*) | 5.4 s bench, 13 s owner (local) |

The owner's set is 8 verified read-aloud clips (3 planted errors), below the
20-clip pilot floor: a strong signal, not a decision. Voxtral heard the owner's
accent far better (*õpin*, *piima*, *Tallinnas* where Whisper wrote *ipin*,
*pima*, *Tallinas*) but once supplied the grammatical form. No free host can
serve it, so production stays on Workers AI; with `requirements-local-asr.txt`
installed and `VOXTRAL_RT_MODEL` set, `cli serve` asks Voxtral first
(`providers/asr.py`).

## Make a trustworthy private corpus in the app

1. Under `cli serve`, practise in `Rääkimine` and choose **Lisa
   hindamiskomplekti** after a useful answer, or record directly in
   `Hindamiskomplekt` for an occasional planted-error read-aloud control. No
   separate upload is required. Only a clip the learner chooses is saved under
   ignored `data/eval/asr/`; ordinary practice audio remains unsaved. A prompt
   or question is stored separately from the transcript, and an ASR draft is
   only a draft. Hosted transcription sends the chosen audio to Cloudflare.
2. Play the clip in the app. Correct the draft to exactly what was audibly
   spoken, including errors; confirm that it was listened to; and mark whether
   an intentionally wrong form was actually spoken. Skip ambiguous clips.
   Audio and transcript hashes seal the review, and changing either requires
   review again. A displayed target, question or ASR draft is never ground
   truth.
3. The CLI offers optional focus-word and error-tag annotation. For a recording
   actually saying “Ma ostsin uus auto”:

   ```bash
   python -m eesti.cli asr-verify data/eval/asr/0000.webm --listened \
     --planted-index 2 --accepted uue --focus 2 --tag morphology
   ```

   Indices are zero-based after Unicode NFC, case folding and punctuation
   removal. `--accepted` names the expected form that would hide the learner's
   error. Optional tags include `numbers`, `names`, `short-answer`,
   `hesitation` and `noise`. An adjacent `.question` is sealed as context; an
   explicit `--question` must match it.
4. Collect clips across ordinary sessions. A first pilot needs at least 20
   verified clips, five error probes and five morphology tokens, plus correct
   controls, short answers, names, numbers and hesitations. Expand before a
   provider decision. These floors do not guarantee statistical confidence or
   pronunciation competence.

## Everyday check of the production engine

`Rääkimine → Kuidas mind kuuldakse` measures only the production recogniser,
from read-aloud sentences the learner confirms and planted object-case probes,
without saving audio (`docs/speaking.md`). It gives a first reading of word
errors and repaired mistakes; comparing engines still needs the verified
corpus above.

## Compare paired engines

Install optional `faster-whisper` locally and download the official TalTech
model's **ct2 subdirectory**. Point `ASR_REFERENCE_MODEL` to that directory.
Neither the model nor its runtime is part of the default dependencies or Cloud
Run image. The reference fixes temperature to zero and ignores question hints.
The Cloudflare request uses production model settings: read-aloud controls get
no target hint; an open answer may get its actual question as context. Compare
hinted and unhinted examples separately. Use the same number/name transcription
policy for both engines.

```bash
python -m eesti.cli eval --suite asr --engine workers-ai \
  --engine faster-whisper --output data/eval/asr-results.json
```

The report includes corpus WER/CER, per-clip outputs, engine fingerprints,
failures, latency, morphology-token errors and aligned false-accept counts. An
unrelated substitution or deletion is an error but not a repaired expected
form. The paired bootstrap compares mean per-clip WER differences and refuses
a decisive result when evidence is incomplete or undersized. Cold reference
loading is part of the first clip's time. Read the tagged cases; aggregate WER
can conceal mistakes in names, numbers and case endings.

Exit 2 means insufficient or unavailable evidence. The `chain` engine is
for diagnostics only. Keep audio, transcripts and reports in ignored
`data/eval/`, never a PR or public workflow artifact. A production change
requires lower false acceptance without unacceptable WER/CER, morphology,
latency, failure or hosting-cost regressions. No report switches providers
automatically.
