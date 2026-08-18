# Where AI is used, where it is not, and where the two collide

An audit of every place a model touches the learner, prompted by a fair
question: when AI checks answers, sets exercises and listens to speech, do those
overlap in ways that hurt?

**They did, in one place, and it was serious.** The rest of the map is cleaner
than expected, mostly because of a decision made early: *generation and grading
are deterministic*.

## The map

| Job | Engine | Can it be wrong? |
|---|---|---|
| Deciding what you practise next | **prerequisite graph** | no model involved |
| Generating a drill | **Vabamorf synthesis + EKK tables** | round-trip validated; ambiguous words refused |
| **Grading a drill** | **string comparison** | no — and free, and offline |
| Mastery, placement, checkpoints | **arithmetic over recorded attempts** | no model involved |
| Checking free writing | LLM chain → Vabamorf offline | yes; engine always shown |
| Transcribing speech | Workers AI → OpenRouter → HF → whisper.cpp | yes |
| Read-aloud comparison | **`difflib` against a known target** | no model judgement |
| Feedback on a spoken answer | LLM chain, over the transcript | yes, **twice over** — see below |

The single most important line is the third. **No model decides whether your
answer was right**, on any exercise, ever. That is why a drill can be graded
offline, instantly, for free, and identically every time — and why a bad day
from a provider cannot cost you a practice session.

**No model sets your homework either.** Every drill, quiz, placement probe and
checkpoint comes from the generators, the topic graph and your own recorded
attempts. Adding a model there would trade something exactly right for something
plausible, in the one place the app has no way to check the answer.

## The collision that mattered

Speech feedback ran the transcript through the same grammar chain as writing.
Reasonable on its face — a transcript is text, and the chain is good at Estonian
text — and wrong, because **a transcript is evidence about two things at once**:
what the learner said, and what the recogniser heard. Nothing in the pipeline can
separate them.

Measured, with a learner who pronounced *kooli* correctly and was heard as
*kohli*:

```
raw       : [('kohli', 'vocab'), ('raamatut', 'obj-case'), ('kohli', 'obj-case')]
```

Two of those three are the recogniser's mistake reported as the learner's — a
vocabulary error and an object-case error on a word nobody said. That is the
exact "confidently wrong answer" failure this project spends its effort avoiding,
and it would have poisoned the error log, whose whole value is that everything in
it is real.

The rule now: **a correction anchored on a word Vabamorf does not recognise is
dropped, whatever its tag.** If a token is not a word, nothing about that token is
worth reporting. Unknown words are recomputed from the text rather than read off
the `vocab` corrections, so the rule holds for LLM engines that never emit those.

```
transcript: [('raamatut', 'obj-case')]        advisory=True
```

The real error survives; the invented one is gone. What remains is marked
**advisory**, and advisory results are shown but never recorded: they must not
reach the review queue or the Notion error log. (Verified: speech has no path to
`queue_failed` — every caller is a deterministic drill.)

## The other overlaps, and why they are fine

- **Writing check and speech feedback share a chain.** Deliberate: an
  object-case error is the same error whether typed or spoken, and it should be
  explained the same way. Only the *trust level* differs, which is what
  `advisory` encodes.
- **ASR and TTS are the same tab and different directions.** TTS voices the
  question (TartuNLP, verified working); ASR hears the answer (Workers AI). No
  shared state.
- **Cost, per recording**: one ASR call, and one LLM call only for open answers.
  Read-aloud makes no LLM call at all — the comparison is `difflib`. At
  $0.00051 per audio minute plus a free-tier LLM, daily practice is rounding
  error.
- **A tripped engine is not retried.** Both chains share one circuit breaker
  (`providers/breaker.py`). Speech needed it more than grammar: four engines at
  120 s each meant an outage cost eight minutes of waiting before saying nothing
  was heard. Now 45 s each, and a dead engine is skipped after two failures.

## What is not measured, and should be said

The eval track (`cli eval`) scores **grammar** models on Estonian, on 1 000
external pairs plus a hand-written set. **Nothing measures ASR quality**, because
there is no Estonian speech benchmark wired up here and no gold recordings of
this learner. So the ASR ranking in `docs/speaking.md` rests on published claims
and provider availability, not on a measurement this project made — stated here
so it is not mistaken for one.

## Rules for anything added later

1. **Grading stays deterministic.** If a new exercise cannot be graded without a
   model, it needs a known target — as read-aloud does — or it is feedback, not
   grading.
2. **Anything derived from a transcript is advisory** and never enters the error
   log.
3. **The engine is always named** in the response, so a Vabamorf-offline
   correction is never mistaken for a full explanation.
4. **Every network engine is optional.** With no keys at all: drills generate and
   grade, the path works, reading works, speaking records and plays back.
