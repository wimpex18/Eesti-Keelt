# ADR-0002: One tutor boundary, and a conversation that never grades

**Status:** Accepted
**Date:** 2026-09-20
**Deciders:** the owner (sole learner and maintainer)
**Follows:** ADR-0001 (code grades; a model's score is advisory evidence), written
into `docs/ai-boundaries.md` rather than as a file.

## Context

P4 left two gaps.

1. **Four model-facing paths, four sets of rules.** `/api/check` (writing),
   `/api/translate`, `/api/speaking/feedback` and `/api/tutor` each call a
   provider themselves. Only `/api/tutor` grounds its prompt in Vabamorf and
   EKK, checks the answer for invented forms, and labels what came back. A rule
   enforced in one of four places is a rule that will be forgotten in the other
   three — the per-correction provenance from P4 is already only on the writing
   path, and the day's budget is only counted in the grammar chain.
2. **Speaking has no partner.** The B1 exam is paired: a discussion, a
   conversation that must reach a decision, and an information-exchange
   role-play (HARNO, checked 2026-09-19). The app can play a question bank and
   record an answer, so the learner practises monologue for a dialogue exam.

Constraints: one learner; free provider tiers with daily caps; the language rule
(Estonian content, Russian explanation); and ADR-0001 — a model may explain and
may produce conversation, but must not decide whether an answer was right.

## Decision

**`eesti/tutor.py` becomes the single boundary for every model call that speaks
to the learner in words** — corrections, explanations, translation, conversation
— and gains a bounded `converse` intent.

Speech **recognition** is not one of them: it turns audio into text and decides
nothing, so it keeps its own chain (`providers/asr.py`), and on the deployment
it runs in the Worker against Cloudflare's binding, where a Python boundary
cannot reach it. It obeys the same daily-allowance rule in the code path it does
own.

- Every intent returns one envelope: `explanation_ru` / `reply_et`, the engine
  that answered, the grounding it was given, and `source: "model"`.
- The boundary owns what was scattered: the day's budget (`providers/budget.py`),
  the grounding check, the Russian-explanation rule, and the advisory label.
- The HTTP surface keeps its routes — the page calls them, and one endpoint per
  job reads better than one endpoint with a switch — but each route is now four
  lines delegating to `tutor`.
- `converse` plays the exam partner over a task from the speaking bank: Estonian
  replies, one question back, at most `MAX_TURNS` turns, never a correction and
  never a verdict. Turn-by-turn state stays with the page; the server holds none.

## Options considered

### Option A: leave the four paths as they are

| Dimension | Assessment |
|---|---|
| Complexity | Low now, higher per rule added |
| Cost | No change |
| Risk | Each new rule must be written four times |
| Familiarity | Highest — nothing moves |

**Pros:** no churn; each route is readable on its own.
**Cons:** provenance, budgets and grounding drift apart; the next boundary rule
lands in one place and is missed in three.

### Option B: one tutor module, routes delegate to it (**chosen**)

| Dimension | Assessment |
|---|---|
| Complexity | Medium: one module grows, four routes shrink |
| Cost | No change |
| Risk | An indirection layer that could become a dumping ground |
| Familiarity | The module already exists and is tested |

**Pros:** one place to enforce ADR-0001, the budget and the grounding check; the
routes stay small and honest; tests point at one module.
**Cons:** `tutor.py` must not become "everything that touches a model" — the
provider chain stays where it is, and the tutor calls it.

### Option C: collapse the routes into `POST /api/tutor` with an `intent` switch

| Dimension | Assessment |
|---|---|
| Complexity | Medium, and pushed onto the page |
| Cost | No change |
| Risk | Breaks a cached page; loses per-route status codes |
| Familiarity | Lowest |

**Pros:** one route, one contract.
**Cons:** the page and the service worker would have to change together, and a
switch over intents hides which failures belong to which job.

## Trade-off analysis

The real choice is **where a boundary rule lives**. B puts it in one module that
already has the grounding check and its tests, at the cost of one more call hop.
C buys nothing B does not, and costs the page. A is cheapest today and is the
option that made the P4 gap in the first place.

For conversation the trade-off is **usefulness against honesty**: a model
partner is the only way to practise a dialogue alone, and it is also the easiest
place to teach a wrong form. So the conversation is allowed to speak Estonian
freely, but every Estonian word it uses is checked against Vabamorf and the ones
it does not know are named to the learner, the exchange is capped, and nothing
it says is recorded as evidence about the learner beyond "a conversation
happened, this long".

## Consequences

**Easier:** adding a rule (a new label, a cap, a refusal) — one module, one test
file. Counting what the tutor costs: the budget is checked and spent in `_ask`,
and the recognition chain checks the same budget for its own lanes.

**Harder:** `tutor.py` is now on the request path for writing checks, so its
failure modes are the writing tab's failure modes; it must keep returning the
deterministic result when no lane answers.

**To revisit:** conversation history is the page's, so a reload loses it —
acceptable for one learner; if conversations become evidence worth replaying,
they belong in the log as their own event type with turns kept.

## Action items

1. [x] `tutor.check_writing`, `tutor.translate`, `tutor.speaking_feedback`,
   `tutor.converse`; routes delegate.
2. [x] Budget checked and spent inside `tutor._ask`.
3. [x] `Vestlus` in Rääkimine: a task from the bank, turn by turn, with the
   model's unknown forms named and the "not graded" caveat.
4. [x] `conversation` events: task, turns, words — never a score.
5. [ ] Revisit if speaking evidence needs the turns themselves (P5).
