# Next session

Paste the prompt below as the first message of a fresh session (local or
cloud). Keep this file current: replace the prompt when its work is done.

```text
Grove (Eesti-Keelt): continue the A0→B1 course (Linear DEV-40) from the units
layer: the unit check, unit completion, Home's session within a unit, homework
and the weekly pace check towards a sitting.

Read first: AGENTS.md, HANDOFF.md, docs/status.md, docs/course-structure.md,
docs/adr/0007-course-units.md, docs/curriculum.md, docs/app-structure.md,
qa/architecture-review.md, then Linear DEV-40 and its latest comment. Run
`git log --oneline -20` and the fast suite (`python -m pytest tests/ -q -n auto`)
and confirm the state the documents describe; correct any that is out of date in
the same change.

Working rules:
- One branch (claude/dev-40-unit-check) and one PR for the session; no new
  Linear issues — follow-up goes in a comment on the existing issue.
- Design is out of scope (a redesign follows): functional, minimal UI changes in
  the existing components; inspect both viewports after web changes.
- Code grades against Vabamorf/EKI forms; never invent a linguistic fact; label
  model-written material; a stage is a target, `level` is CEFR only for
  official material.
- Effort high. Subagents for research and review, not for parallel edits.

Build, tests first:
1. The unit check: five server-graded items per core topic and per revisited
   rule (`eesti/units.py`), recorded as a `unit-checked` event and replayed; a
   unit is complete when its core topics are mastered and its check passed.
   Revision units (19, 27, 29, 30) check their stage's topics and carry the
   checkpoint where `checkpoint` is set.
2. Kursus and Home: a unit's complete state; Home names the session within the
   current unit (*Ühik 3 · 2/5*) beside the due-review count.
3. Placement into a unit: the assessment's entry becomes the first unit with a
   core topic it did not pass; earlier units are navigation skips.
4. Homework set at the end of a session (due cards plus one short skill task)
   and the weekly pace check when a sitting is chosen, both pure functions of
   the evidence like `eesti/planning.py`.
Then update docs/status.md, docs/course-structure.md ("Built today"),
qa/architecture-review.md, HANDOFF.md and this prompt; comment on DEV-40.
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
