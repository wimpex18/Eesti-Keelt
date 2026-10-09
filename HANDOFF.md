# Handoff

Current task: remove the Impeccable design tool and all its traces on
`claude/remove-impeccable`. PR #125 merged; stale branches deleted.
Earlier (merged): course units (ADR-0007), unit 1, nominative object, osaalus, EKI credit,
unit check, skipping a unit or every unit before a chosen one, the start of the
B1 exam loop (writing tasks with a code checklist, *Eksamipäev*), restored
reminder push handler. Claude Haiku 5.5 passed ADR-0008's bar at effort high
(9 Oct) and leads the grammar/tutor chain, Workers AI behind it; prompt caching
and a byte bound under 100K tokens; its own prompt (`grammar.CLAUDE_PROMPT`).
Parallel Opus sessions: `qa/opus-sessions.md` (waves, file ownership, merging);
`cli worktree-data` gives a worktree reference data, never learner data.
Fast suite and browser journeys (both engines) green.
Next: the owner merges the remove-impeccable PR, runs `bash deploy/set-llm-key.sh
ANTHROPIC_API_KEY` in Cloud Shell, then `smoke` with `deep: true`; then wave 1
of `qa/opus-sessions.md` (S1, S5, S6, S7), per `qa/next-session.md`.
Owner: set a spend limit on the Anthropic account; send the permission requests
in `qa/source-permission-requests.md` (Monday); re-subscribe to reminders on each
device; verify a backup with `cli verify-backup`.
Linear is paused (owner, 9 Oct): follow-ups live here and in PRs.
Uncommitted task paths: none after the commit. No secrets revealed.
