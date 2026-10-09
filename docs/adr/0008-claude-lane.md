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
   The cheapest effort level that passes is pinned. On 9 Oct 2026 `low` and
   `medium` missed the bar and `high` passed it (10/10 with 8/8 clean; 13/40
   with 19/20 clean; `docs/ai-providers.md`), so Haiku leads
   `grammar.LLM_PREFERENCE` at effort `high`, with Workers AI behind it.
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
6. **Prompts stay under 100K tokens and are cached.** A request over 90 000
   UTF-8 bytes is refused before sending; the system prompt carries the cache
   breakpoint. Haiku has its own grammar prompt, written to Anthropic's Haiku
   5.5 guidance, and the eval scores the prompt the app sends.

## Consequences

- Haiku answers learners once `ANTHROPIC_API_KEY` is on Cloud Run
  (`deploy/set-llm-key.sh`); until then, and whenever Haiku cannot answer,
  Workers AI does. Reverting is one line in `grammar.LLM_PREFERENCE`.
- Inference runs outside the EU (`inference_geo` is `global` or `us`); the
  privacy notes say so.
- A paid run of the eval uses the GitHub secret through `eval.yml` (track,
  sample and effort are inputs); all six runs of 9 Oct cost about $0.06.
