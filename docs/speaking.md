# Speaking: what is worth building, and what to run for it

## The constraint that shapes everything

The B1 speaking exam is **paired**. Task 1: the examiner asks from a topic sheet,
the two candidates answer *in turn*, and then they talk *to each other* to reach
agreement, working from an idea card. Task 2: a role-play — one candidate phones
an institution, the other is its employee.

Both halves are graded on interacting with another person: turn-taking, picking
up their point, negotiating. A solo record-and-score loop trains almost none of
it. So the app does the parts a phone can honestly do — **the questions in the
exam's shape, the other side voiced by TTS, and hearing yourself back** — and
does not pretend to grade.

There is **no pronunciation score**, deliberately. Forced alignment yields
timings, not correctness; converting that into feedback is a research project;
and EKI already publishes free
[pronunciation exercises](https://sonaveeb.ee/pronunciation-exercises/). A
transcript is used for exactly one honest thing: showing what the recogniser
*heard*, so you can compare it with what you meant.

## Estonian speech recognition, probed rather than assumed

Checked directly in August 2026, because the last round of this research found
four Estonian research APIs returning 500 while their docs looked healthy.

| Option | State |
|---|---|
| **TalTech `whisper-large-v3-turbo-et-verbatim-2604`** | MIT, ungated. 1 400 h verbatim Estonian + ~4 000 h broadcast news + 500 h English, so it handles English terms inside Estonian sentences. **GGML build published 2026-06-17** (1.6 GB) — runs in whisper.cpp on CPU. |
| `…-et-verbatim` (the older one) | Superseded; its own card points at 2604. Earlier notes in this repo recommended it — corrected. |
| Hosted inference for those models | **None.** `inferenceProviderMapping` is empty: nobody rents them. |
| `openai/whisper-large-v3` | Five providers on Hugging Face, supports Estonian, less accurately than the fine-tune. This is the hosted fallback. |
| `api.tartunlp.ai/speech-to-text` | Still 404. Archived in 2024. |
| `tekstiks.ee` | Up, free for non-commercial use, but a SvelteKit app with no documented public API — its own page points at `est-asr-pipeline` for self-hosting. |
| Browser Web Speech API | Free, no infrastructure, but Estonian is not reliably supported in Safari or Chrome. Feature-detected, never assumed. |

**The finding that matters: the best Estonian model cannot be rented, but it can
now be run.** The GGML build means whisper.cpp on Apple Silicon transcribes
faster than real time on CPU — so the most accurate option is also the free and
private one, on the laptop you already own. That settles the privacy question
too: text is disposable, a voice is biometric, and this way the voice never
leaves the machine.

## Running it locally (MacBook)

```bash
brew install whisper-cpp
curl -L -o ~/models/et-verbatim.bin \
  https://huggingface.co/TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604/resolve/main/ggml/ggml-model.bin

export WHISPER_CPP_BIN=$(which whisper-cli)
export WHISPER_CPP_MODEL=~/models/et-verbatim.bin
```

`/api/asr` then reports `local: true` and the speaking tab transcribes without
sending anything anywhere.

## The hosted fallback (phone)

Set `HF_TOKEN` — the same secret the model eval already uses — and
`/api/transcribe` falls back to generic Whisper through Hugging Face. Worse at
Estonian, but it works from a phone, where whisper.cpp cannot run.

With **neither** configured, the tab still records and plays back, which is most
of its value, and says so instead of showing a dead button.

## What other apps do

Nothing here is exotic; the market splits three ways. Consumer apps
(Duolingo, Babbel, Speakly) use either the browser's Web Speech API or a cloud
ASR — **Azure Speech and Google Cloud STT both support `et-EE`**, both are paid
past a free tier, and both mean uploading the learner's voice. Serious Estonian
tooling self-hosts TalTech's models, which is what `est-asr-pipeline` and
`tekstiks.ee` are. This app takes the second path where the hardware allows and
degrades to the first only as a fallback, which is the same shape as every other
provider chain here: **own the core, rent nothing you cannot lose.**
