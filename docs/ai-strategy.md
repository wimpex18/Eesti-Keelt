# AI strategy: which model, when it is worth it

## The question that actually matters

Not "which LLM is best" but **which parts of this app should use an LLM at all**.
Most of what a language learner needs is deterministic, and deterministic is
better: it is free, instant, offline, and it cannot be confidently wrong.

| Job | Use an LLM? | Why |
|---|---|---|
| Generating drills | ❌ no | Vabamorf gives real forms. An LLM would hallucinate inflections. |
| Grading drills | ❌ no | String comparison against a synthesized form is exact. |
| Word forms, paradigms | ❌ no | Vabamorf + sonapi are authoritative. |
| **Judging a free-text sentence** | ✅ **yes** | Telicity is semantics. Vabamorf sees the case written; only a model can judge whether the action is completed. |
| **Explaining an error in Russian** | ✅ yes | The one job with no deterministic substitute. |
| Generating exam-style writing prompts | ✅ yes | Cheap, low-risk, unbounded variety. |
| Scoring writing against B1 criteria | ⚠️ careful | Useful signal, but never present it as a real exam mark. |

The rule: **an LLM adjudicates and explains; it never generates the linguistic
facts.** That keeps hallucination out of the layer where a learner would silently
absorb it.

## Model options, August 2026

Free tiers, from the current comparisons:

| Provider | Free tier | Notes |
|---|---|---|
| **Google Gemini 2.5 Flash** | ~1 500 req/day, 1M token context | Most generous real free tier; ~10–15 RPM. |
| **Groq** | ~30 RPM, up to 14 400 req/day on small Llama | Fastest inference (~320 tok/s on Llama 3.3 70B). |
| **Cerebras** | ~1M tokens/day | Llama 3.3 70B class. |
| **Mistral** | 1B tokens/month, 2 RPM | ⚠️ the free "Experiment" tier **requires opting into training**. |
| **Anthropic / OpenAI** | paid | No standing free tier; cheap at this volume. |

There is no unlimited free tier in 2026; every one carries rate limits and no SLA.

### Recommendation

**Primary: a paid frontier model, but only on the free-text path.** At a few
sentences a day the cost is cents per month — far below the threshold where a
free tier's constraints are worth accepting. Quality matters disproportionately
here because a wrong grammar explanation gets memorised.

**Two caveats against the free options for *this* app:**

1. **Mistral's free tier requires training opt-in.** The text being submitted is a
   language diary — mistakes, personal writing, exam practice. Sending that to be
   trained on is a poor trade for a tool whose whole point is a private error log.
2. **Estonian is a low-resource language.** Frontier-model quality gaps widen on
   Estonian morphosyntax exactly where this app is pointed. A model that is 95 %
   as good at English may be far worse at judging täissihitis vs osasihitis.

**Where free tiers do fit:** the bulk, low-stakes, non-authoritative jobs —
generating practice prompts, drafting role-play cards, translating a gloss. Groq
or Gemini are well suited, and the provider chain already makes adding one a
single class.

### An Estonian-specific option worth tracking

`TartuNLP/gec-llm` — open-weight Llama-2/Llammas fine-tunes for Estonian
grammatical error correction, published by the University of Tartu. Too heavy for
a laptop (7B class, needs a GPU), but it is the only *Estonian-tuned* option and
would remove the low-resource concern entirely. Worth revisiting if a smaller
distilled version appears.

## Verified provider table (probed August 2026)

| Provider | Free allowance | Note |
|---|---|---|
| **OpenRouter** | 50 req/day; **1 000/day after a one-time $10 credit purchase** | One key, 412 models, 15 currently `:free`. 20 req/min either way. The $10 is an account threshold, not consumption. |
| **Groq** | generous, per-model limits | Fastest inference. |
| **Cloudflare Workers AI** | **10 000 neurons/day**, shared across models | Runs *inside* Cloudflare — no egress, no third-party key. |
| Google Gemini 2.5 Flash | ~1 500 req/day, 1 M ctx | Most generous standalone tier. |
| Mistral | 1 B tokens/month | ⚠️ free tier **requires opting into training**. |

**Probe before pinning.** Ids are withdrawn silently, and a withdrawn `:free` id
is the worst case: the paid one with the same name keeps working, so the name
still looks right while every call 404s. Verified live —
`openai/gpt-oss-120b:free` is **absent** from OpenRouter while
`openai/gpt-oss-120b` persists. `python -m eesti.cli models` re-probes.

Free ids with `structured_outputs` (needed for the JSON contract), largest first:
`dots-studio/dots-3-note-preview:free` (512 K ctx),
`google/gemma-4-26b-a4b-it:free` (262 K),
`nvidia/nemotron-3-super-120b-a12b:free` (262 K, the pinned default),
`openai/gpt-oss-20b:free` (131 K), `nvidia/nemotron-nano-9b-v2:free` (128 K).

## Testing the "it knows other languages, so it knows Estonian" hypothesis

That hypothesis is reasonable and it is testable, so `eesti/evals/gec.py` tests it
instead of assuming. 18 Estonian sentences, two scores:

- **recall** — of the 10 with planted errors, how many were caught
- **precision** — of the 8 **already correct** sentences, how many were left alone

Precision is what separates models. A checker that flags every partitive scores
perfect recall and is actively harmful, because it teaches that every partitive is
wrong. Estonian is low-resource and the judgement needed here (genitive for a
completed whole object; partitive for ongoing, partial or negated) is exactly the
language-specific semantics that thins out first in a multilingual model.

```bash
python -m eesti.cli eval --provider openrouter --model <id>
```

Exits non-zero below 0.8 on either score, so it can gate a deploy. **Run this
before believing any recommendation in this document, including its own.**

### First real result (18 Aug 2026)

`nvidia/nemotron-3-super-120b-a12b:free` — the pinned default, a 120B model with
a 262 K context:

| | |
|---|---|
| recall | **0.50** — caught 5/10 planted errors |
| precision | **0.50** — left alone only 4/8 correct sentences |

**It fails in the harmful direction.** It flagged `Ma ostsin uue auto` and
`Ma sõin suppi` — both correct — and missed both irregular-verb errors
(`minen`→`lähen`, `teesin`→`tegin`). A learner following it would be taught that
correct Estonian is wrong.

This is the hypothesis tested and answered: **being a large, capable multilingual
model does not confer Estonian object-case competence.** Estonian is low-resource
and this judgement is exactly the language-specific semantics that thins out
first. The eval existed precisely because this could not be assumed either way.

Caveat on the number: two of the eighteen cases were lost to HTTP 429 and a
malformed reply, so 0.50/0.50 is a lower bound. The client now throttles to
OpenRouter's 20 req/min limit and retries 429/5xx, so later runs measure the
model rather than our impatience.

**Next step:** score `google/gemma-4-26b-a4b-it:free` and `openai/gpt-oss-20b:free`,
then a paid frontier model as the ceiling. If no free model clears ~0.8 precision,
the honest conclusion is that this one job is worth paying cents a month for.

## Competitive landscape

What the 2026 AI language apps do, and what they leave open:

| App | Strength | Price |
|---|---|---|
| Langua | conversation depth, voice naturalness | ~$24/mo |
| Speak | structured beginner curriculum | ~$20/mo |
| Praktika | avatar roleplay, cheapest | ~$8/mo |
| Duolingo Max | habit-building; weak on speaking | — |
| Memrise | spaced repetition + MemBot chat | — |
| **ABC Pilot** (`abcpilot.eu`) | **the direct competitor** — Estonian only | A2 €29/mo, B1 **€49/mo**, B2/C1 €99/mo (Oct 2026) |

**ABC Pilot is the one to study.** Built by Saan Targaks, an Estonian language
school, on official HARNO materials: a 6-month plan, AI speech recognition, instant
AI writing feedback, and exam-format listening/reading/writing tasks, for 2 500+
learners. It does not publish which models it uses.

It validates the concept and prices it — B1 prep is worth €49/month to enough
people to sustain a business. What it cannot do is the thing below.

The consistent criticism across reviews: **feedback is shallow** — brief, generic,
and not tied to the learner's recurring errors. Reviews also note the split that
matters here: general LLM tools are good at explanation and bad at habit; dedicated
apps are good at habit and shallow at feedback.

**None of the general AI tutors support Estonian meaningfully** — it is absent
from their language lists. ABC Pilot does, and charges €49/month for B1.

### What that implies for this app

Do not compete on conversation practice or gamification — those are solved and
expensive. Compete on the thing every review says is missing, which is also the
thing a personal tool can uniquely do:

**A closed loop against one learner's documented errors.** The Notion `Vead`
database already records what actually goes wrong, tagged. Drills generated from
those tags, weighted toward tags that recur, is something no commercial app can
offer — they don't have the error log. Reviews independently endorse the format:
sentence cards testing a grammar point *in context*, not a rule in the abstract.

## Sequenced plan

1. **Now** — LLM only for free-text adjudication + Russian explanation. Everything
   else deterministic. *(built, needs a key)*
2. **Next** — weight drill selection by tag frequency in the `Vead` DB, so practice
   follows the error log automatically.
3. **Later** — spaced repetition (FSRS) over items previously failed.
4. **Optional** — a free-tier provider for prompt generation, behind the same chain.
