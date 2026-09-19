# AI boundaries

Where a model touches the learner, and where code decides.

## The map

| Job | Engine | Model judgement? |
|---|---|---|
| What to practise next | prerequisite graph | no |
| Generating a drill | Vabamorf synthesis, EKK tables, attested corrections | no — round-trip validated, ambiguous words refused |
| **Grading a drill** | string comparison | **no** |
| Mastery, placement, checkpoints | arithmetic over recorded attempts | no |
| Spelling in free writing | Vabamorf dictionary | no — merged into every answer |
| Subject–verb agreement | Vabamorf tags + synthesis (rules from GiellaLT's Estonian CG) | no |
| Rection (`rektsioon`) | EKK SÜ 64 list + Vabamorf | no — only confusions the handbook records |
| Other free-writing errors, explanations | TartuNLP GEC → LLM chain → Vabamorf offline | yes; engine always named |
| Meaning, conversation scoring | LLM chain → Vabamorf offline | authorised as advisory evidence, not built |
| Transcribing speech | Workers AI Whisper (production), provider chain locally | yes |
| Read-aloud comparison | `difflib` against the known sentence | no |
| Feedback on a spoken answer | LLM chain over the transcript | yes, and advisory |

Code grades drills, review and FSRS; a model never supplies a drill's answer
key. A model may explain, tutor, judge meaning and score open production
(writing, conversation) where code cannot decide. Its score names the engine,
is advisory evidence for readiness only, and never moves mastery or FSRS.

## Deterministic checks win over a model

Spelling, agreement and rection findings are added to every grammar answer,
whichever provider answered. Where a provider already covered the same word,
its explanation is kept; deterministic evidence is added, never used to
overrule prose that says more.

## Transcripts are advisory

A transcript mixes what the learner said with what the recogniser heard. So:

- a correction anchored on a word Vabamorf does not recognise is dropped,
  whatever its tag (unknown words are recomputed from the text);
- results are marked `advisory` and never reach the review queue or the
  Notion log (speech has no path to `queue_failed`). The transcript is kept
  in the evidence log as practice, never as graded evidence.

## Rules for anything new

1. Code decides where it can. Where it cannot, a model may grade, and the
   verdict names the engine.
2. Anything derived from a transcript is advisory and never enters the error
   log.
3. The response names the engine that answered.
4. Every network engine is optional. With no keys: drills generate and grade,
   the path, reading and review work, speaking records and plays back.
