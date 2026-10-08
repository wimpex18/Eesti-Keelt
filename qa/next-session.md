# Next session

Paste the prompt below as the first message of a fresh session (local or
cloud). Keep this file current: replace the prompt when its work is done.

```text
Grove (Eesti-Keelt): implement the next part of the architecture review —
the A0→B1 course structure (Linear DEV-40), starting from the current state.

Read first, in this order: AGENTS.md, HANDOFF.md, docs/status.md,
qa/architecture-review.md, PRODUCT.md, docs/curriculum.md, docs/app-structure.md,
then Linear DEV-40, DEV-36, DEV-41, DEV-42, DEV-45 (team Development, project
Eesti-Keelt). Run `git log --oneline -20`, the fast suite
(`python -m pytest tests/ -q -n auto`) and confirm the state those documents
describe before planning; correct any document that is out of date in the same
change.

Working rules for this session:
- One branch (claude/dev-40-course-structure) and one PR for everything in this
  session; never a PR per issue, no parallel sessions, no sub-branches.
- Do not create Linear issues; record follow-up as comments on existing ones.
- Design is out of scope (a redesign follows later): keep UI changes functional
  and minimal, in the existing components.
- Code grades against Vabamorf/EKI forms; never invent a linguistic fact; label
  model-written material; `level` means CEFR only for official material.
- Effort high. Use subagents for research and review, not for parallel edits.

Steps:
1. Interview me (a few questions at a time) on: unit size and cadence; what a
   unit contains (goal, words, dialogue, grammar, reading, listening, speaking,
   writing, check); how blocks, topics and modes map to Home, Course, Review,
   Exam and the four skills; placement into units; homework and a weekly plan
   towards the sitting; how a unit links to the matching Keeleklikk unit.
2. Write the spec (`docs/course-structure.md` once agreed, current-state
   wording) and an ADR: the A0 unit in full; units A0→B1 mapped to HARNO's
   topics and EKI's grammar-competence profiles; how each of the 43 topic IDs
   maps into units (IDs stay stable, ADR-0005); which units need new generators
   or material; what the redesign inherits.
3. Build the first slice on the same branch:
   - the A0 unit: sounds and quantity with EKI's pronunciation exercises and
     recordings (check terms first), greetings and survival phrases, numbers,
     first words (EKI picture dictionary, credited);
   - the nominative total object in `obj-case` (imperative, impersonal,
     *tuleb/vaja* + da-infinitive, plural total object), keyed by Vabamorf;
   - partitive subject and existential sentences (*Poes on leiba*);
   - EKI's credit on every item built from EVS phrases (offline packs,
     test-out, placement, review cards — `docs/status.md`).
   Tests first for each; full suite and browser journeys
   (`python -m pytest tests/test_e2e_journeys.py --browser -q -n 4`) green.
4. Update docs/status.md, qa/architecture-review.md (decision states),
   HANDOFF.md and this file's prompt for the session after; comment on DEV-40.
```

## When the Claude API key is in `.env`

```text
Grove (Eesti-Keelt): add and evaluate the Claude Haiku 5.5 tutor lane (Linear
DEV-38). Local session. Read AGENTS.md, HANDOFF.md, docs/ai-providers.md,
docs/ai-boundaries.md, docs/adr/0002 and 0005, qa/architecture-review.md
("Claude lane"), DEV-38 and DEV-44. Load the claude-api skill before writing
Claude API code (official anthropic SDK, no OpenAI-compatibility shim). One
branch, one PR. Scope the 3.5 s `_throttle` in eesti/providers/llm.py to evals;
add the native lane (no temperature; explicit effort; JSON-schema outputs;
refusal = failed lane; prompts ≤100K tokens; registry, budget lane, Allikad,
eval workflow). Ask me before running the paid eval
(`python -m eesti.cli eval --provider anthropic`, hand and --track external,
Haiku 5.5 low and medium, Sonnet 5.5 once) and agree the promotion margin first.
Baseline GPT-OSS-120B: hand 8/10 caught, 8/8 clean; external 2/40, 16/20 clean.
If it clearly wins, draft the ADR (paid lane with a monthly ceiling). Never ask
for or paste keys in chat.
```
