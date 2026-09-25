# ADR-0003: Ground truth for speech evaluation

**Status:** Accepted. Architecture choice: ADR-0005.

The deciding corpus is the owner's own learner speech, recorded locally in
`Rääkimine → Hindamiskomplekt`. A displayed prompt or an ASR transcript is not
ground truth. A human must listen and correct the transcript before marking it
verified. Audio/text hashes invalidate verification after edits. Raw recordings,
reviewed transcripts and benchmark output all remain private and uncommitted.

Use the existing harness, with named engines on identical recordings. Measure
corpus WER/CER, latency including failure coverage, morphology-sensitive tokens
and explicit wrong-form-to-expected-form false acceptance. Deletions and unrelated
substitutions must not count as corrected-away errors. A “verbatim” model name
is not evidence that it preserves learner mistakes.

Start with a small verified pilot; enlarge it across sessions, correct controls,
planted errors, short answers, names, numbers and hesitations before changing
production. A paired bootstrap is useful uncertainty evidence, not a quality
certificate. No sample-size or learner-quality claim follows from native
broadcast WER. Public native speech is a separate regression corpus; it cannot
replace learner recordings for false acceptance. Train/test overlap must be
checked before using any public corpus to compare fine-tuned models.

A second, lighter tier runs in ordinary practice: the learner says right after
reading a displayed sentence whether it was read as written. That is a human
judgement without a replay, so it is reported apart from verified clips and
never feeds a provider switch alone (`eesti/asrcheck.py`).

`docs/asr-evaluation.md` is the operational workflow and model comparison.
The current checkpoint has no learner evaluation recordings. Production stays
on Cloudflare while the TalTech reference path is available for measurement.
