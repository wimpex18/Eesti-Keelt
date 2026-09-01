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

"Use it, don't build it" is only a decision if the learner can reach it, and for
a long time this was a line in a document with no link on the page. The panel
now ends with two outbound links — EKI's pronunciation exercises and the
[A1–B1 situational phrase collections](https://sonaveeb.ee/learn) — which is
also how the plan's "seeded from `sonaveeb.ee/learn` dialogues" gets honoured
without scraping a site whose maintainers asked nobody to scrape it. The
question bank stays hand-written to the exam's shape; the phrase material stays
where its authors put it.

## Estonian speech recognition, probed rather than assumed

Checked directly in August 2026, because the last round of this research found
four Estonian research APIs returning 500 while their docs looked healthy.

| Route | State | Estonian | Cost |
|---|---|---|---|
| **Cloudflare Workers AI `@cf/openai/whisper-large-v3-turbo`** | live | Whisper's 99 languages, and takes a `language` pin | **$0.00051 per audio minute** + free daily neurons |
| **OpenRouter** | 38 audio-input models; one **free** (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`), Gemini Flash from ~$0.00000004/audio-token | multilingual | free tier exists |
| Hugging Face `openai/whisper-large-v3` | five providers | generic | free tier |
| **TalTech `whisper-large-v3-turbo-et-verbatim-2604`** | MIT, ungated, 1 400 h verbatim Estonian + ~4 000 h broadcast news. GGML build published 2026-06-17 (1.6 GB) | **best** | **nobody hosts it** — `inferenceProviderMapping` is empty |
| **TalTech `Voxtral-Mini-3B-2507-estonian`** | Apache-2.0, published 2026-08-25. An audio-*understanding* model, not a Whisper — it takes an instruction with the audio. GGUF by a third party (`mradermacher`), not by TalTech | reports 5.05 % WER, on ten recordings, which the card says not to read as a benchmark | **nobody hosts it** — re-probed 2026-09-01, mapping empty |
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
4. **Local whisper.cpp**, then **local Voxtral** — kept as a bonus for whoever
   runs `serve` on their own laptop, where they are both accurate at Estonian
   and the only options where the voice never leaves the machine.

whisper.cpp goes in front of Voxtral, and the reason is evidence rather than
preference. Both are TalTech and both are Estonian; the difference is what is
known about them. The verbatim Whisper has the published Estonian track record.
Voxtral's card reports 5.05 % WER and says in the same paragraph that the
validation set is ten recordings and "should not be treated as a broad estimate
of Estonian ASR quality". Neither is measured on this project's own material,
nobody has said anything about the new one — 48 downloads, no likes, no
discussion — and **being newer is not a result**. Turn one off to compare them.

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

Or TalTech's Estonian Voxtral, through llama.cpp's multimodal CLI —
`llama-server` cannot do this yet, since an OpenAI-shaped
`/v1/audio/transcriptions` is an open feature request upstream rather than a
merged endpoint:

```bash
huggingface-cli download mradermacher/Voxtral-Mini-3B-2507-estonian-GGUF \
  Voxtral-Mini-3B-2507-estonian.Q4_K_M.gguf \
  Voxtral-Mini-3B-2507-estonian.mmproj-f16.gguf --local-dir ~/models/voxtral-et

export VOXTRAL_BIN=$(which llama-mtmd-cli)
export VOXTRAL_MODEL_PATH=~/models/voxtral-et/Voxtral-Mini-3B-2507-estonian.Q4_K_M.gguf
export VOXTRAL_MMPROJ=~/models/voxtral-et/Voxtral-Mini-3B-2507-estonian.mmproj-f16.gguf
```

All three variables or none. The `mmproj` file is the audio encoder: without it
the binary still loads and still answers, about audio it never received — a
confident transcript of nothing, which is the worst failure available here — so
the lane refuses to start rather than half-start. `docs/local-llm.md` has what
is actually known about the model.

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


## Where the voice goes

Worth stating plainly, because the answer changed and the code went on claiming
the old one.

The original plan kept ASR **local** for a specific reason: text is disposable
and a voice is biometric, and `neurokone.ee` renders no data-protection policy
at all without JavaScript. That reasoning was sound and it still is.

It did not survive the move to a hosted app. There is no local engine on Cloud
Run, so recognition runs on **Cloudflare Workers AI** through the Worker's
binding, and the recording leaves the device. `/api/transcribe`'s docstring
went on saying "the local engine is preferred and nothing is written to disk"
for some time after that stopped being true — which is worse than never having
said it.

What holds now:

- The audio is **not stored**: not on the origin, not in the Worker, not in any
  database. It exists in memory for one request; the transcript is what
  survives.
- The learner is told **before** pressing record, in the speaking panel, in
  Russian. A disclosure in a document nobody opens is not a disclosure.
- Running `cli serve` locally with whisper.cpp keeps the voice on the machine.
  That option is real and it is the private one; the hosted app cannot match it.
