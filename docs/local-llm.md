# Running EstLLM yourself

The Estonian-adapted model this project wanted from the start, on hardware you
own — because on 2026-08-20 nobody hosts it, and probably nobody will.

## Why there is no API to call

`tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125` is a Llama 3.1 8B with roughly 35B
tokens of continued Estonian pretraining and instruction tuning. The paper
reports it beating the multilingual base it came from on Estonian tasks, which
speaks directly to this project's own measurement: a 120B *general* model scored
**0.50 recall / 0.50 precision** on Estonian object case and failed in the
harmful direction, flagging correct Estonian as wrong.

So the model is the right idea. The distribution was the problem — and it has
partly stopped being one, which is worth stating loudly because this table said
otherwise for months:

| Model | Hosted, re-probed 2026-09-01 | Lane |
|---|---|---|
| `tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125` | **featherless-ai, status `live`, task `conversational`** | `huggingface`, and `local` |
| `tartuNLP/Llama-3.1-EstLLM-70B-Instruct-0826` | none *(new: published 2026-08-17)* | `HUGGINGFACE_MODEL` the day somebody hosts it |
| `tartuNLP/Apertus-EstLLM-8B-Instruct-0326` | none | — |
| `TalTechNLP/Voxtral-Mini-3B-2507-estonian` | none *(new: published 2026-08-25)* | `voxtral`, local only |
| `TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604` | none | `whisper.cpp`, local only |

The August probe found "nobody hosts any of them" and that was true when it was
written. It is not true now: the exact model this project pins is served by an
inference provider through Hugging Face. **A claim about somebody else's
infrastructure is a measurement, and measurements go stale silently** — this
one did, in the direction that would have kept the project from noticing an
option it had been waiting for.

What that changes: reaching EstLLM no longer strictly requires a machine. It
requires an HF token and a paid third party instead, which is a different
trade, not obviously a better one — the local lane stays the default because it
is free, private, and answers to nobody's pricing page. What it does mean is
that the sentence "this is not a gap that is about to close" was wrong within
three weeks, and the honest version is that nobody should plan around either
state lasting.

**Two models exist now that did not when this was written**, and both are now
wired rather than only noted. A 70B EstLLM (2026-08-17) — the same lineage,
roughly nine times the weights, out of reach of a Mac mini at ~40 GB for Q4,
and hosted by nobody; `HUGGINGFACE_MODEL` is why reaching it the day somebody
does will not be a code change. And TalTech's Estonian Voxtral (2026-08-25),
which is the first serious answer to the speaking lane's open question — the
app's recogniser is Cloudflare's Whisper today, and `docs/speaking.md` says
plainly that a miss may be the recogniser rather than the learner's mouth.

**One correction to how that was written down.** The note said "Estonian
Voxtral with GGUF builds", which credits TalTech for something they did not
publish: the repository holds bfloat16 safetensors only. The quantisations are
`mradermacher/Voxtral-Mini-3B-2507-estonian-GGUF`, a third-party requantiser.
That is not a footnote — whoever pulls those files is trusting a converter as
well as a trainer, and the model card's terms say nothing about the conversion.

Neither model is measured on this project's eval, and neither is adopted on the
strength of being new. What changed is that both are now *reachable*: an
unreachable option is one nobody can measure, and "we should try it some day"
has been this project's most expensive sentence.

## What is actually known about the Estonian Voxtral

| | |
|---|---|
| Published | 2026-08-25, `TalTechNLP/Voxtral-Mini-3B-2507-estonian` |
| Licence | Apache-2.0, following `mistralai/Voxtral-Mini-3B-2507` |
| Size | 4.68 B parameters; Q4_K_M is the practical local build |
| What it is | an audio-**understanding** model, not a Whisper: it takes an instruction with the audio |
| Trained on | 149 397 examples over seven tasks — verbatim ASR, subtitles, stenograms, news writing, summarisation, QA, speech translation |
| Reported | **5.05 % WER** at the selected checkpoint |
| Hosted by | **nobody.** `inferenceProviderMapping` is empty, re-probed 2026-09-01 |

Two things about that WER, both from the card itself rather than from us: the
validation set is **ten recordings**, and the authors write that it "should not
be treated as a broad estimate of Estonian ASR quality or as directly
comparable with public benchmark results". Some training targets were generated
by another model, so stylistic errors can be inherited. This is a checkpoint
-selection number, not a benchmark result, and the app treats it as one.

**What people say about it: nothing.** 48 downloads, zero likes, no discussion
found anywhere, no coverage. That is worth writing down rather than leaving as
an absence, because "new model, must be better" is exactly the reasoning this
project's eval exists to refuse. There is no community verdict to lean on, so
the only verdict available is a measurement somebody runs.

Because it is an instruction-following model, **the prompt is load-bearing**:
asked nothing in particular it will as happily return a summary, a subtitle
track or a news story, all of which it was trained to produce from the same
recording. `providers/asr.py` asks it for a verbatim transcription explicitly,
and a test asserts that it does.

### Running it

`llama-server` is not a route: an OpenAI-shaped `/v1/audio/transcriptions` on
llama.cpp is an open feature request, not a merged endpoint, and audio through
the server is still called experimental upstream. So this lane shells out to
the multimodal CLI, exactly as the whisper.cpp lane shells out to `whisper-cli`.

```bash
# the weights and the audio encoder -- both, or it cannot hear
huggingface-cli download mradermacher/Voxtral-Mini-3B-2507-estonian-GGUF \
  Voxtral-Mini-3B-2507-estonian.Q4_K_M.gguf \
  Voxtral-Mini-3B-2507-estonian.mmproj-f16.gguf --local-dir ~/models/voxtral-et

export VOXTRAL_BIN=$(which llama-mtmd-cli)
export VOXTRAL_MODEL_PATH=~/models/voxtral-et/Voxtral-Mini-3B-2507-estonian.Q4_K_M.gguf
export VOXTRAL_MMPROJ=~/models/voxtral-et/Voxtral-Mini-3B-2507-estonian.mmproj-f16.gguf
```

All three or nothing. Without the `mmproj` file the binary still loads and
still answers — about audio it never received, which is the worst failure
available here, so the lane refuses to start rather than half-start.

It sits **behind** whisper.cpp in the chain. Both are TalTech and both are
Estonian; the difference is what is known about them, and the verbatim Whisper
has the published Estonian track record. Turn one off to compare them.

## What is known about EstLLM, and by whom

This is where the two models differ most, and it is worth being explicit
because they arrived in the same week and it would be easy to treat them alike.

EstLLM has **a paper** — *EstLLM: Enhancing Estonian Capabilities in
Multilingual LLMs via Continued Pretraining and Post-Training*
(arXiv:2603.02041), from TartuNLP and TalTechNLP under the Estonian Ministry of
Education and Research's language-technology programme. Continued pretraining
on ~35 B tokens from `meta-llama/Llama-3.1-8B`, then SFT on ~764 k examples and
DPO. It reports consistent gains over both the base model and its
instruction-tuned variant across Estonian linguistic competence, knowledge,
reasoning, translation and instruction-following, while holding English
performance — and its logits-based scores are on the public **EuroEval**
leaderboard, which is somebody else's harness rather than its authors' own.

The Estonian Voxtral has a model card, ten validation recordings, and an
explicit warning from its authors not to read the number as a benchmark.

Neither has been measured on **this** project's eval, which is the only one
that asks the question this app cares about: Estonian object case, graded
against Vabamorf. A benchmark suite says a model is better at Estonian in
general. It does not say it will stop flagging `Ma sõin suppi` as wrong, which
is precisely what the 120 B general model this project measured did.

## Reaching EstLLM without a machine

`HF_TOKEN` and the `huggingface` provider, which is `LLM_PREFERENCE`'s second
entry — directly behind `local`, ahead of every general-purpose model. That is
not a new argument: it is the *same* Estonian-adapted model as the local lane,
on hardware somebody else owns. What separates the two is who pays and who can
read the request.

```bash
export HF_TOKEN=...            # routed onward to featherless-ai
python -m eesti.cli eval --provider huggingface
```

**What is asserted and what is not.** The provider mapping is read from the
model's own metadata and the router speaks the OpenAI shape this client already
sends. What this repository cannot verify is that a request completes: the
router answers **401 before it routes**, so an unauthenticated probe returns 401
for a real id and a made-up one alike and proves nothing. Only a call with a
token settles it, and this repository must never hold one. The lane is offered,
not promised, and `cli eval` is what turns it into a number.

**What does exist is quantised weights**, and an 8B model is small. That makes a
Mac mini a perfectly reasonable place to run it.

## Setting it up

Ollama is the shortest path; LM Studio and `llama.cpp --server` work identically
because all three expose an OpenAI-compatible `/v1`.

```bash
# on the Mac mini
brew install ollama
ollama serve                     # listens on 127.0.0.1:11434

# ~4.9 GB for Q4_K_M; Q5_K_M is ~5.7 GB and a little better
ollama pull hf.co/mradermacher/Llama-3.1-EstLLM-8B-Instruct-1125-GGUF:Q4_K_M
```

Twelve quantisations are published. `Q4_K_M` is the usual balance; on 16 GB of
unified memory `Q5_K_M` also fits comfortably alongside everything else.

Then point the app at it:

```bash
export LOCAL_LLM_URL=http://localhost:11434/v1
python -m eesti.cli serve
```

That is all. The `local` lane turns on when `LOCAL_LLM_URL` is set and is tried
**before** the metered providers — not as a guess about quality, but because it
is the one lane running a model built for Estonian, and it is free, private and
unmetered. Nothing changes if it is unset.

To use a different model or quant:

```bash
export LOCAL_LLM_MODEL=hf.co/mradermacher/Apertus-EstLLM-8B-Instruct-0326-GGUF:Q4_K_M
```

## Reaching it from the deployment

`cli serve` on the same machine needs nothing further. The Cloud Run deployment
is a different question: it has no route to your home network, and it should not
get one by opening a port.

The right shape is a **Cloudflare Tunnel**, which this project is already set up
for — the app already sits behind a Worker and Access.

```bash
brew install cloudflared
cloudflared tunnel login
cloudflared tunnel create estllm
cloudflared tunnel route dns estllm estllm.<your-domain>
cloudflared tunnel run --url http://localhost:11434 estllm
```

Then set `LOCAL_LLM_URL=https://estllm.<your-domain>/v1` on the Cloud Run
service. Put an Access policy in front of it exactly as the app has, or the
tunnel is an open inference endpoint on the internet.

**Weigh this honestly before doing it.** A tunnel means the Mac mini has to be
awake for the writing check to use the Estonian model, and when it is asleep the
chain steps over the lane and asks OpenRouter — which is the designed behaviour
and costs nothing. Running local-only during study sessions is simpler and gives
up very little.

## What is still unknown

**Whether EstLLM is actually better at this job.** It has never been scored. The
argument for it is a paper's general claim plus a measured failure by a general
model, which is a good reason to *test* it and not a result.

Test it the way every other model here was tested:

```bash
LOCAL_LLM_URL=http://localhost:11434/v1 \
  python -m eesti.cli eval --provider local
```

18 Estonian sentences, ten with planted errors and eight already correct. The
number that matters is **precision** — leaving correct Estonian alone — because
that is where the general model failed and where a wrong answer teaches the
learner the opposite of the rule.

Two outcomes are both useful. If it clears ~0.8, the Estonian model was the
answer and this lane earns its place. If it does not, then the honest conclusion
stands from `ai-strategy.md`: this one job is worth cents a month on a paid
model, and no amount of local hardware substitutes for that.
