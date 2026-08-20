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

So the model is the right idea. The distribution is the problem:

| Model | Hosted by an inference provider |
|---|---|
| `tartuNLP/Llama-3.1-EstLLM-8B-Instruct-1125` | none |
| `TartuNLP/gec-llm` | none |
| `tartuNLP/Llammas-base` | none |
| `TalTechNLP/whisper-large-v3-turbo-et-verbatim` | none |

Hugging Face's router serves 132 models and not one Estonian one. OpenRouter
carries no Baltic-specialist model at all. This is not a gap that is about to
close: Estonian is a 1.1-million-speaker language and hosted inference follows
demand.

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
