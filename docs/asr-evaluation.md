# ASR choice and evaluation

The deployed app transcribes in the Worker (`deploy/worker.ts`): first the
owner's Mac mini (the home service, `eesti/asrserver.py`), reached through a
Workers VPC Service on a Cloudflare Tunnel; when it does not answer within
25 s, Cloudflare Workers AI `@cf/openai/whisper-large-v3-turbo`. Under local
`cli serve`, `eesti/providers/asr.py` walks its own chain, Voxtral Realtime
first when installed.

## Measured

| Engine | Bench WER | Bench CER | Owner's 8 clips WER | Planted errors "fixed" (bench + owner) | Median latency |
|---|---|---|---|---|---|
| Workers AI Whisper turbo | 20.0% | 3.6% | 36.4% | 0 of 15 | 2.8 s (hosted) |
| TalTech Whisper et-verbatim (`faster-whisper`, CPU int8, beam 5) | 5.7% | 0.7% | 7.3% | 2 of 15 | 4.4 s on 4 Apple M5 threads |
| TalTech Voxtral Realtime (`voxtral-rt`, Apple M5 GPU, BF16) | 6.5% | 1.0% | 7.3% | 1 of 15 | 5.4 s bench, 13 s owner |

The owner's set is 8 verified read-aloud clips with 3 planted errors, below the
20-clip pilot floor: a strong signal, not proof. Both TalTech engines heard the
owner's accent (*õpin*, *piima*, *Tallinnas*) where Workers AI wrote *ipin*,
*pima*, *Tallinas*; each occasionally supplies the grammatical form
(`vastus` → *vastust*), which Workers AI did not.

## Where each engine runs

| Engine | Where | Why |
|---|---|---|
| [TalTech Whisper et-verbatim](https://huggingface.co/TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604) | the home service on an Intel Mac (the owner's 2018 Mac mini), CPU | runs without a GPU; 1.6 GB |
| [TalTech Voxtral Realtime](https://huggingface.co/TalTechNLP/Voxtral-Mini-4B-Realtime-estonian-2609) | the home service on Apple silicon; `cli serve` with `requirements-local-asr.txt` and `VOXTRAL_RT_MODEL` | needs Apple's GPU (8.9 GB); no hosted endpoint, and streaming needs vLLM on CUDA |
| [Cloudflare Whisper turbo](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/) | the Worker | free, hosted, always there; the fallback |

`deploy/home-asr/README.md` sets up the home service. `docs/speaking.md`
describes what the learner sees.

## The benchmark

`python -m eesti.cli asr-bench` writes `data/eval/asr-bench/`: 20 EKI
*kõnekorpus* sentences read by native speakers (EKI's text is the truth), and
16 TartuNLP-synthesised learner sentences, 12 with one planted error each
(`Ma ostsin uus auto`: the recogniser must not hand back *uue*) and 4 correct
controls (`eesti/evals/asr_bench.py`). Truth is known by construction, so the
seal carries `provenance` instead of a listening confirmation. It ranks
engines on mishearing and silent correction; it is not a learner's voice.

## The owner's verified clips

1. Under `cli serve`, practise in `Rääkimine` and choose **Lisa
   hindamiskomplekti** after a useful answer, or record directly in
   `Hindamiskomplekt`. Only a chosen clip is saved, under ignored
   `data/eval/asr/`; ordinary practice audio is not.
2. Play the clip, correct the draft to exactly what was spoken, including
   errors, and confirm. Audio and transcript hashes seal the review; changing
   either needs review again. A target, question or ASR draft is never truth.
3. Annotate from the CLI when useful:

   ```bash
   python -m eesti.cli asr-verify data/eval/asr/0000.webm --listened \
     --planted-index 2 --accepted uue --focus 2 --tag morphology
   ```

   Indices are zero-based after NFC, case folding and punctuation removal.
   `--accepted` is the form that would hide the error. Tags include `numbers`,
   `names`, `short-answer`, `hesitation` and `noise`.
4. A pilot needs at least 20 verified clips, five error probes and five
   morphology tokens.

`Rääkimine → Kuidas mind kuuldakse` measures only the production recogniser,
without saving audio.

## Comparing engines

```bash
python -m eesti.cli eval --suite asr --folder data/eval/asr-bench \
  --engine workers-ai --engine faster-whisper --output data/eval/asr-results.json
```

Engines: `workers-ai`, `faster-whisper` (`ASR_REFERENCE_MODEL` = the TalTech
**ct2** directory), `voxtral-rt` (`VOXTRAL_RT_MODEL`), and the local
`whisper.cpp` and `voxtral` (llama.cpp) lanes. Neither local runtime is in the
Cloud Run image. The report gives corpus WER/CER, per-clip outputs, engine
fingerprints, latency, morphology-token errors and aligned false accepts; the
paired bootstrap refuses a verdict on undersized evidence (exit 2). A deletion
or unrelated substitution is an error, not a false accept. Keep audio,
transcripts and reports in ignored `data/eval/`. No report switches engines
automatically; a switch needs fewer false accepts without WER, morphology,
latency or cost regressions.
