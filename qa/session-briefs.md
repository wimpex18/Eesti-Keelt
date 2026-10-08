# Session briefs

Ready-to-paste prompts for the next sessions of the October 2026 programme
(`qa/architecture-review.md`, Linear DEV-35..DEV-56). Written 8 October 2026 on
base `faa477d`. Paste one brief as the first message of a fresh session.

## Before starting a brief

- Merged on `main`: PR #111 and the PRs from S1 (DEV-35), S2 (DEV-54) and
  S4 (DEV-37, DEV-39). Each PR edits `HANDOFF.md`; when resolving conflicts keep
  the newest present-state note.
- Local session: run in a new worktree. Cloud session: works for briefs A and C
  (repository, Linear and web only). A cloud checkout has no git-ignored data
  (`data/*.db`, `audio.db`, `data/exam/`, `.env`): build the word list with
  `python -m eesti.cli fetch-data && python -m eesti.cli build && python -m eesti.cli export`
  if tests need it, and never ask for credentials in chat.
- Model: Opus 5.5. Effort `high` for spec and answer-key work; `xhigh` for long
  unattended runs.

---

## Brief A — Course structure spec, A0→B1 (DEV-40). Next after the merges.

```text
Grove (Eesti-Keelt) — course structure spec, Linear DEV-40 (team Development/DEV,
project Eesti-Keelt). This is a specification session: interview me, write a spec,
propose an ADR. Do not implement features yet.

Read first: AGENTS.md, HANDOFF.md, PRODUCT.md, docs/status.md, docs/curriculum.md,
docs/app-structure.md, qa/architecture-review.md (sections "Content and features",
"Three audiences", "Market"), and Linear DEV-40, DEV-41, DEV-42, DEV-45, DEV-36.

Owner decisions already made: a complete, practice-first path from A0 to B1 that
learners use alongside Keeleklikk (0–A2) and Keeletee (B1), plus B1 exam
preparation; Grove makes no video lessons; explanations in Russian, then
Ukrainian, then English, with Estonian material shared; private sources stay
owner-only until written permission; no embedding model.

Inputs to use: EKI grammar-competence profiles (etLex API
https://etlex.eki.ee/etLex/api/v1.0/gramprofiles?project=etLex — 546 can-do
statements; terms not stated, so use for scope, do not copy text), HARNO's 15 A2
topics and B1 task formats, the 43 topics in `eesti/curriculum.py` with their
generators, the missing grammar list in the review (nominative total object,
partitive subject, plural cases, modal verbs, indefinite pronouns, word formation,
relative clauses, negation outside present/past), and the material pipeline
(C1–C6) in the review.

Deliver:
1. Interview me (AskUserQuestion, a few questions at a time) on: unit size and
   cadence; what a unit contains (goal, words, dialogue, grammar, reading,
   listening, speaking, writing, check); how blocks, topics and modes map to
   navigation (Home, Course, Review, Exam, four skills); placement into units;
   homework; how a unit links to the matching Keeleklikk unit.
2. docs/spec/course-structure.md (or a path I approve): A0 unit in full; the unit
   list A0→B1 mapped to HARNO topics and EKI profile levels; how each existing
   topic ID maps into units (stable topic/rule IDs, ADR-0005); which units need
   new generators or material; what the redesign sessions inherit.
3. A draft ADR for the course structure.
4. Linear: the build steps as a checklist in one comment on DEV-40; no new issues.
Small PR, branch with the issue ID, stage named paths only, I merge.
```

---

## Brief B — Claude Haiku 5.5 lane and eval (DEV-38). When the API key is in `.env`.

```text
Grove (Eesti-Keelt) — Claude Haiku 5.5 tutor lane, Linear DEV-38 (team
Development/DEV, project Eesti-Keelt). Local session (needs .env).

Read first: AGENTS.md, HANDOFF.md, docs/ai-providers.md, docs/ai-boundaries.md,
docs/adr/0002 and 0005, qa/architecture-review.md ("Model lane"), Linear DEV-38
and DEV-44. Load the claude-api skill before writing Claude API code and follow it
(official anthropic Python SDK; no OpenAI-compat shim).

Facts (platform.claude.com, 8 Oct 2026): claude-haiku-5-5, 1M context, 128K
output, $0.10/$0.50 per MTok for prompts ≤100K tokens ($0.50/$2.50 above). It
rejects temperature ≠ 1 (eesti/providers/llm.py sends 0 today); thinking is on by
default at effort medium — set output_config.effort explicitly; JSON via
output_config.format; refusals are HTTP 200 stop_reason "refusal" with no
server-side fallback — treat as a failed lane.

Work: scope the 3.5 s _throttle to evals; native lane with KNOWN_KEYS, budget lane,
licence/engine registry, Allikad, eval workflow choice, set-llm-key.sh; prompt-size
guard ≤100K tokens (single requests, no compaction); offline tests. Then ask me
before running `python -m eesti.cli eval --provider anthropic` (hand and
--track external; Haiku 5.5 at low and medium, Sonnet 5.5 once) and agree the
promotion margin first. Baseline GPT-OSS-120B: hand 8/10 caught, 8/8 clean;
external 2/40 caught, 16/20 clean. If it clearly wins, draft the ADR (paid lane with
a monthly ceiling; order Claude Haiku 5.5 → Workers AI → deterministic). Never ask
for or paste keys in chat. Small PRs, branch with the issue ID, I merge.
```

---

## Brief C — Exam fidelity after the spec (DEV-41)

```text
Grove (Eesti-Keelt) — exam fidelity, Linear DEV-41, built on the approved course
spec (DEV-40). Read AGENTS.md, HANDOFF.md, docs/exam-native.md, the course spec,
qa/architecture-review.md ("The real exam, task by task" and the exam-prep
blueprint), and DEV-41. Plan with me which HARNO task types to build first (listening
has none today), then implement in small PRs: item types keyed by code to text
spans, both writing tasks per level on the real clock, HARNO criteria and rated
samples beside the learner's text with a content-point checklist, item review after
mocks, an Eksamipäev page. Speaking is never scored. Branch with the issue ID; I
merge.
```

## Later, in order

DEV-42 explanation languages (Ukrainian first) · DEV-45 practice patterns ·
DEV-43 Litestream (after the 7–8 Nov 2026 sittings) · DEV-46 harvests and source
notes · DEV-47 learner pilot · redesign sessions last.
