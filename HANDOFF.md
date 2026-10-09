# Handoff

Current task: DEV-40/41/38 on branch `claude/dev-40-course-structure`, PR #125 (one PR).
Done: course units (ADR-0007, `eesti/units.py`), unit 1, nominative object, osaalus,
EKI credit everywhere, unit check (`eesti/unitcheck.py`), Claude Haiku 5.5 lane
(evaluation-only, ADR-0008), restored reminder push handler, and the start of the
B1 exam loop (ADR-0009): both writing tasks with a code checklist
(`eesti/writingtasks.py`), *Eksamipäev* (`eesti/examday.py`), practice from reading
misses; a late profile no longer redraws the start screen over the learner's
next step. Research and decisions: ADR-0009, `qa/opus-sessions.md` (8 Opus briefs).
Fast suite and browser journeys (both engines) green.
Next: the owner reviews and merges PR #125; merge rebuilds the origin, then run
`smoke` with `deep: true`. Then `qa/next-session.md` (material pipeline → HARNO
B1 task types → session and Home).
In progress (9 Oct): Haiku 5.5 lane with prompt caching, a byte bound under
100K tokens and its own prompt (`grammar.CLAUDE_PROMPT`); the paid eval runs on
GitHub (the key is a GitHub secret only), then unit skipping and the Opus plan.
Owner: set a spend limit on the Anthropic account; re-subscribe to reminders
on each device (the push handler was missing 24 Sep–9 Oct); send the EKI
permission draft; verify a nightly backup copy with `cli verify-backup`.
Decision taken by default, for the owner to confirm: unit 1 leads the next step
only for a learner who has mastered nothing beyond it; nothing is skipped.
Uncommitted task paths: none after the commit.
Preserve unrelated package.json and untracked .agents/, .claude/agents/,
.claude/settings.local.json, .claude/skills/, .codex/, .github/agents/,
.github/hooks/, .github/skills/, .impeccable/decisions/learning-redesign.json,
.impeccable/live/. No secrets revealed.
