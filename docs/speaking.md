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

## What can honestly be checked, and what cannot

An earlier version of this file said, flatly, that nothing here scores you. That
was right about **acoustic** scoring and too broad, because it also ruled out
something quite different and entirely sound.

|  | Acoustic pronunciation scoring | Read-aloud comparison | Open-answer feedback |
|---|---|---|---|
| Input | waveform | two strings | text |
| Needs | phoneme models, alignment, an invented scale | `difflib` | the grammar chain that already exists |
| Output | *"your /õ/ is 62 % correct"* | *"it heard **kohli** where you were asked to say **kooli**"* | *"raamatut → raamatu, obj-case"* |
| Built? | **no** | **yes** | **yes** |

**Read aloud** (`Loe ette`): the target is known, so comparing what the
recogniser heard against what you were asked to say is deterministic and has no
model judgement in it. Word by word, because *"7/9"* is actionable and *"78 %"*
is not — the two that were missed are the two to say again. The caveat travels
with the number wherever it is shown: this measures what an ASR model heard,
which is a proxy for intelligibility and not a phonetics grade. A miss can mean
you mispronounced it *or* that the model is weak on accented Estonian.

**Answer a question** (`Vasta küsimusele`): once transcribed, a spoken answer is
text — and this project already knows what to do with Estonian text. It goes
through the same grammar chain that checks writing, so an object-case error in
speech is caught the same way it is in an essay, plus word count and pace when
the client reports a duration. 100–130 words a minute is ordinary conversational
Estonian; the number is shown plainly rather than converted into a fluency score
nobody defined.

**Still not built:** scoring the audio itself. Forced alignment yields timings,
not correctness; converting that into feedback is a research project; and EKI
already publishes free
[pronunciation exercises](https://sonaveeb.ee/pronunciation-exercises/).

## Estonian speech recognition, probed rather than assumed

Checked directly in August 2026, because the last round of this research found
four Estonian research APIs returning 500 while their docs looked healthy.

| Route | State | Estonian | Cost |
|---|---|---|---|
| **Cloudflare Workers AI `@cf/openai/whisper-large-v3-turbo`** | live | Whisper's 99 languages, and takes a `language` pin | **$0.00051 per audio minute** + free daily neurons |
| **OpenRouter** | 38 audio-input models; one **free** (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`), Gemini Flash from ~$0.00000004/audio-token | multilingual | free tier exists |
| Hugging Face `openai/whisper-large-v3` | five providers | generic | free tier |
| **TalTech `whisper-large-v3-turbo-et-verbatim-2604`** | MIT, ungated, 1 400 h verbatim Estonian + ~4 000 h broadcast news. GGML build published 2026-06-17 (1.6 GB) | **best** | **nobody hosts it** — `inferenceProviderMapping` is empty |
| `api.tartunlp.ai/speech-to-text` | 404 | — | dead since 2024 |
| `tekstiks.ee` | up, free non-commercial, but a SvelteKit app with no documented API | good | — |
| Browser Web Speech API | free, no infrastructure | not reliably supported in Safari or Chrome | — |

### The correction

An earlier version of this file recommended running whisper.cpp locally with
TalTech's GGML build. That is the most accurate and most private option and it
is **the wrong recommendation for this app**: this deploys to Cloudflare, so
"runs on your MacBook" happens on a machine the server is not, and a learner on
a phone gets nothing from it.

So the chain is ordered by **where the app actually runs**:

1. **Cloudflare Workers AI** — the platform the app deploys to, credentials
   (`CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`) already provisioned for the
   model eval, and at half a thousandth of a dollar per audio minute a year of
   daily practice costs less than a coffee. It accepts `language="et"`, so
   Estonian is pinned rather than guessed — a few seconds of accented speech is
   exactly what Whisper guesses wrong — and an `initial_prompt`, which is fed the
   question being answered so the vocabulary is biased to the topic.
2. **OpenRouter**, using an audio-capable model, free tier included.
3. **Hugging Face**, generic Whisper.
4. **Local whisper.cpp**, last — kept as a bonus for whoever runs `serve` on
   their own laptop, where it is both the most accurate at Estonian and the only
   option where the voice never leaves the machine.

A *failing* engine falls through to the next rather than ending the attempt.
That differs from the grammar chain on purpose: grammar degrades to an offline
Vabamorf pass, and there is no offline engine behind speech.

### Why not an Estonian LLM

The obvious question, so it is answered in the code as well as here: **EstLLM
cannot do this.** `tartuNLP/Llama-3.1-EstLLM-8B-Instruct` is a text model with no
audio encoder — it cannot turn a recording into words at any price. The Estonian
*speech* models are TalTech's, and nobody rents them.

Where an Estonian-tuned model does belong is one step later: judging the
**transcript** — did the answer address the question, and was the grammar sound.
That is text, and it runs through the LLM chain that already exists.

## Running it locally (optional)

Only useful when serving from your own machine, and then it is the best option:

```bash
brew install whisper-cpp
curl -L -o ~/models/et-verbatim.bin \
  https://huggingface.co/TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604/resolve/main/ggml/ggml-model.bin

export WHISPER_CPP_BIN=$(which whisper-cli)
export WHISPER_CPP_MODEL=~/models/et-verbatim.bin
```

## With nothing configured

The tab still records and plays back, which is most of its value, and says so
instead of showing a dead button. `/api/asr` reports exactly which engines this
deployment has.

## What other apps do

Nothing here is exotic; the market splits three ways. Consumer apps (Duolingo,
Babbel, Speakly) use either the browser's Web Speech API or a cloud ASR —
**Azure Speech and Google Cloud STT both support `et-EE`**, both are paid past a
free tier, and both mean uploading the learner's voice. Serious Estonian tooling
self-hosts TalTech's models, which is what `est-asr-pipeline` and `tekstiks.ee`
are. This app rents the platform it already runs on and keeps the self-hosted
route available, which is the same shape as every other provider chain here:
**own the core, rent nothing you cannot lose.**
