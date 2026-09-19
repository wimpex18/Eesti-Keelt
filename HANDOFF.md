# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

Preparing the UI/UX redesign for the Super App. Design context is in
(`PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`); instructions are in
`AGENTS.md`, with `CLAUDE.md` an identical copy. Python (3.14) and the Python
dependencies float on the latest stable.

## Next step

1. Redesign the UI to `DESIGN.md`: multi-accent palette, web fonts, gradients
   and elevation, gamification, an overall progress score.
2. Build model grading for meaning and conversation (`docs/ai-boundaries.md`).

## Uncommitted / undecided

- Local agent, skill, hook and settings folders under .claude and .github
  are untracked and not committed.

## Blockers
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer
  (it then falls back to `AGENTS.md`).
