---
paths:
  - "eesti/**/*.py"
---

# Python: state, data flow, derivation

## Paths, connections, state
- Resolve paths at call time (`config.*`), never bind a path or connection at import; pass the connection into functions.
- One home per value: never keep a second copy of a path or setting another module can redirect.
- State that must survive a Cloud Run cold start (breaker counts, caches protecting a third party) lives in a snapshotted database, not a module global.
- Rebuilding a table also rebuilds every cache derived from it.

## Every value needs a writer and a reader
- When adding a reader, find its writer; when adding a writer, find its caller. Nothing fails when one side is missing — the feature just looks finished.
- Every route has a caller; every enumerated state has a code path that sets it.
- Check a presence by counting rows, never by `exists()`: opening a SQLite file creates it with its schema.
- A queue needs a drain that exists on the deployment, not only in the CLI.
- In a dispatch, make sure an inner condition can actually be true for the branch it sits in.
- Refusal and failure messages must be true for the input in front of the learner, and keep the provider's own error reason (`grammar.why_failed`).
- "Nobody there" (EOF, Ctrl-C) raises; it is never an empty answer that grades as wrong.

## Derived, never hand-maintained
- Derive lists from the thing they describe (tabs from the page, topics from `TOPICS`, keys from `env.KNOWN_KEYS`). If it cannot be derived, test both directions.
- One job, one implementation: shared cleaning, grading and rendering live in one module (`harvest/clean.py`, `item.GradedItem`, `api/render.py`).
- Resolve database ids to learner-readable names where the API answers.

## Language and content
- Forms come from Vabamorf through `morph.case_forms` (round-trip validated); gate on part of speech first (`wordlist.declines`) — the synthesiser invents paradigms for adverbs.
- Every caller of one linguistic fact uses the same function.
- Do not state a rule harder than EKK does ("usually", not "always").
- Prefer attested corrections to generated distractors; measure a distractor on real sentences before shipping it.
- When reviewing a selection step (filters, sampling, limits), check the whole returned set, not individual rows; a `LIMIT` after an ordering can silently show one slice.
- Before trusting a rule that refuses inputs, measure what share of real inputs it refuses.
- Review cards keep their schedule but refresh their prompt and answer text.
- Third-party courtesy is enforced in code (throttle, lock, stored answers), not in a docstring.
- Read the whole third-party response before choosing a field.
