# ADR-0004: A model may write material; only code may key it

**Status:** Accepted. Applies ADR-0001 through the tutor boundary in ADR-0002.

## Decision

A model may propose a question stem, task situation or dialogue turn. Every
gradable field must pass deterministic verification before the item is stored:

- A reading answer appears verbatim exactly once in the source text, and the
  question does not contain its own answer.
- An Estonian form round-trips through Vabamorf. Unknown forms or unverified
  keys cause the item to be discarded.
- The verified item, generator version and authoring engine are recorded in
  the learner evidence log. Attempts replay against that stored item, not a
  fresh model response.
- Grading compares with the stored key; it does not ask a model at answer time.

Model authorship is labelled in the interface. Generated material does not
supply morphological keys, alter the deterministic planner, or change mastery
or FSRS. This keeps linguistic evidence and model-written practice separate
(`docs/ai-boundaries.md`).

## Current use

`eesti/comprehension.py` verifies and grades text-bound reading questions.
`eesti/tutor.py::propose_questions` proposes them. The reader stores a
`questions-made` event and records verified answers as `comprehension`
practice. A text without verifiable questions presents none.
