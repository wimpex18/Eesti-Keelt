# ADR-0008: A paid Claude lane, with a ceiling

**Status:** Accepted (owner, 9 Oct 2026). **Scope:** model lanes for
explanations, tutoring, advisory feedback and content drafting (Linear DEV-38).
Supersedes ADR-0005's "no paid inference host" for this lane only.

## Context

The automatic tutor and grammar lane is Workers AI GPT-OSS-120B, which caught
8 of 10 planted errors with 8 of 8 clean sentences left alone, but only 2 of 40
attested learner errors (16 of 20 clean). Explanations in Russian, Ukrainian and
English, speaking and writing feedback, and drafted learning material all need
a stronger model. Claude Haiku 5.5 costs $0.10 / $0.50 per million input /
output tokens up to a 100K-token prompt; Claude Opus 5.5 $4 / $20, half that
through the Batch API.

## Decision

1. **Haiku 5.5 for learner-facing model work** — explanations, the tutor,
   writing and speaking feedback, the conversation partner — through Anthropic's
   SDK (`eesti/providers/claude.py`). **Opus 5.5 for drafting material**, offline,
   through the Batch API and the verification in ADR-0009; never at answer time.
2. **The lane answers learners only after its own eval passes:** on the hand set
   at least 8 of 10 errors caught with 8 of 8 clean; on the external track at
   least 12 of 40 attested learner errors caught with at least 16 of 20 clean.
   Effort `low` and `medium` are both run; the cheaper level that passes is
   pinned. Until then the lane is evaluation-only (`cli eval --provider
   anthropic`, `eval.yml`), outside `grammar.LLM_PREFERENCE`.
3. **A ceiling, enforced twice:** the app's daily cap (2 000 calls, 300 for
   guests; `providers/budget.py`) and a spend limit set on the Anthropic
   account. A test requires every paid lane to carry a cap. Reaching the
   account's limit is a spent lane, not a broken one: it does not trip the
   circuit breaker.
4. **Models stay advisory (ADR-0001).** Code keys drills and decides mastery and
   FSRS; a model's output is labelled with its engine. A refusal or an empty or
   truncated reply is a failed lane, never an empty explanation.
5. **What leaves the app is written down.** Learners' text goes to Anthropic,
   which deletes API inputs and outputs within 30 days and does not train on them
   by default (`eesti/licences.py`, `/api/sources`). Audio never goes to Claude,
   which takes none: speech is recognised first, and the learner confirms the
   transcript (ADR-0003).

## Consequences

- Workers AI stays the automatic lane until the eval passes; the switch is one
  line in `grammar.LLM_PREFERENCE` and its docs.
- Inference runs outside the EU (`inference_geo` is `global` or `us`); the
  privacy notes say so.
- A paid run of the eval needs the owner's `ANTHROPIC_API_KEY` in `.env` and as
  a GitHub secret; a full run costs about $0.10.
