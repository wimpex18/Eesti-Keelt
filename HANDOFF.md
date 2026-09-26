# Handoff

## Current state
PRs #72–#85 are merged. The production deep smoke passes for the current `main`
image. Cloud Run has one instance with mounted EKI audio and HARNO exam storage;
Workers AI GPT-OSS-120B is the grammar/tutor lane; Workers AI is production ASR.

## Current task
Branch `claude/evs-examples` (PR #86): the word card's *Näited* shows EVS
phrases with Russian (`evs_example`, `cli import-evs`), credited to EKI. Meaning
cards in Järjekord show one phrase and, from the second review, a tile builder
(*Koosta fraas*, `review.js`). EVS idioms fold under *Väljendid*. The form
index keeps only forms Vabamorf reads back, and a word tapped in a text is
looked up with its sentence (*selles lauses*, `lookup.py`). Speech: `cli
asr-bench` plus the owner's 8 sealed clips; Voxtral Realtime (7% WER vs
Workers AI 36% on the owner's voice) is the first lane of local `cli serve`
only (owner chose Mac-only; `requirements-local-asr.txt`, `VOXTRAL_RT_MODEL`).

## Next step
User reviews the PR and merges; Cloud Build re-imports EVS in the image. After
deploy run the `smoke` workflow with `deep: true`. Uncommitted paths: none.

## Open questions
Whether to let EstLLM write comprehension questions in local `cli serve`
(Estonian-only work that code verifies), and whether to raise the grammar
lane's token budget: a long sentence returned `empty reply (length)`.

## Remaining checks
Chrome reminder delivery; 12 more owner clips to reach the ASR pilot floor.
