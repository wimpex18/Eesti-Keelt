# ADR-0004: A model may write the material; only code may key it

**Status:** Accepted
**Date:** 2026-09-20
**Supersedes nothing.** Narrows ADR-0001 (grading authority) and sits inside
ADR-0002 (the tutor is the only boundary a model speaks across).

## Context

The architecture plan rejected "an LLM planner or LLM-generated answer keys"
as *not reproducible, and a violation of the linguistic-authority rule*. That
was read afterwards as a licensing restriction, which it never was: the owner
has keys for Mistral, NVIDIA and Workers AI, and the material licences are
settled (private study).

The real constraint is narrower than "no models in content":

- A **key** — the string an answer is graded against — must be derivable and
  stable. Vabamorf's `case_forms` round-trips; a model's answer does not, and
  may differ next week.
- The **material** a question is asked *about* has no such requirement. A
  question stem, a task situation, a dialogue turn is text the learner reads.
  Nothing is graded against it.

Meanwhile `lugemine` is the one exam part the app could not practise at all:
`learner.SKILL_EVENTS["lugemine"]` was empty, so reading produced exposure and
nothing else, and the HARNO reading tasks now in the app (their text extracted
from the exam board's own PDFs) had no questions attached.

## Decision

A model may **author** content. It may never **key** it.

Concretely, for any generated item:

1. The model proposes the item, through `tutor` (ADR-0002), inside the daily
   per-lane allowance.
2. **Code verifies every gradable field before the item is ever stored**, and
   verification is a property of the text, not an opinion:
   - a reading answer must appear **verbatim, exactly once** in the source
     text (so the key is the text's own words, not the model's);
   - an Estonian form must round-trip through Vabamorf;
   - a question must not contain its own answer;
   - a word the morphology does not know drops the item (`tutor._grounded`).
3. The **verified item is stored in the evidence log** with the engine that
   wrote it and a generator version. Reproducibility comes from persistence,
   not from the model: the same question is asked the same way next month, and
   an attempt can be replayed against it. The log, not the library: reference
   data is archived once and restored to each new container, so a question
   written there would vanish at the next cold start and the text would be paid
   for again.
4. Grading is a string comparison against the stored span. No model is asked at
   answer time, ever.

An item that fails verification is discarded silently; the learner sees fewer
questions, never a wrong one.

## What this does not open

- **No model-set answer key for morphology.** Forms come from Vabamorf.
- **No model planner.** `planning.plan` stays a pure function of evidence.
- **No model mastery or FSRS input.** ADR-0001 stands: a model's judgement is
  advisory evidence for readiness only.
- **No silent authorship.** Anything a model wrote says so, with its engine, in
  the interface.

## Consequences

- Reading becomes practisable: questions over real texts, graded by code,
  recorded as `comprehension` events that count towards the `lugemine` skill
  floor the planner balances.
- The same shape extends later to listening (over a transcript) and to writing
  task situations, without another decision.
- Generation costs a model call per text, once, and the result is stored as a
  `questions-made` event in the learner log, not in the harvested corpus.
- A text with no verifiable questions produces none, and says so.

## Implementation

`eesti/comprehension.py` (verification, storage, grading — spans are matched as
whole words, so a key is never a fragment of a longer one), the model call in
`eesti/tutor.py::propose_questions`, `/api/read/questions/{id}` and
`/api/read/answer`, and the reader's question list in `eesti/web/js/reading.js`.
