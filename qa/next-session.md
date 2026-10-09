# Next session

Paste the prompt below as the first message of a fresh session (local or
cloud). Keep this file current: replace the prompt when its work is done.

```text
Grove (Eesti-Keelt): continue ADR-0009's order — the B1 exam loop before the
7–8 Nov 2026 sittings. First the material pipeline (`qa/opus-sessions.md`,
brief 1), then HARNO B1 reading and listening task types on checked material
(brief 6), then the session and Home (brief 8).

Read first: AGENTS.md, HANDOFF.md, docs/status.md, docs/adr/0007, 0008 and
0009, docs/course-structure.md, qa/architecture-review.md, qa/opus-sessions.md,
then Linear DEV-36, DEV-41 and their latest comments. Run `git log --oneline -20`
and the fast suite, and correct any document that is out of date.

Working rules: one branch and one PR; no new Linear issues; design out of scope
(functional, minimal UI in existing components, both viewports inspected); code
grades against Vabamorf/EKI; never invent a linguistic fact; there is no human
reviewer, so model-written material passes ADR-0009's automatic checks and is
labelled; effort high; subagents for research and review, not parallel edits.
If ANTHROPIC_API_KEY is now in `.env`, ask the owner before running the paid
eval (`cli eval --provider anthropic`, hand and external, effort low and medium)
against ADR-0008's bar, and promote the lane only if it passes.
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
