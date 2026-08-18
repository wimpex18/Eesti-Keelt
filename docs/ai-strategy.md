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

## Competitive landscape

What the 2026 AI language apps do, and what they leave open:

| App | Strength | Price |
|---|---|---|
| Langua | conversation depth, voice naturalness | ~$24/mo |
| Speak | structured beginner curriculum | ~$20/mo |
| Praktika | avatar roleplay, cheapest | ~$8/mo |
| Duolingo Max | habit-building; weak on speaking | — |
| Memrise | spaced repetition + MemBot chat | — |

The consistent criticism across reviews: **feedback is shallow** — brief, generic,
and not tied to the learner's recurring errors. Reviews also note the split that
matters here: general LLM tools are good at explanation and bad at habit; dedicated
apps are good at habit and shallow at feedback.

**None of them support Estonian meaningfully.** Estonian is absent from the major
AI tutors' language lists, which is why this exists at all.

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
