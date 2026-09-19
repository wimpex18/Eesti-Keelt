# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; under 30 lines.

## Task in flight

Preparing the UI/UX redesign for the Super App. Done: Impeccable design
context is in (`PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`);
instructions moved to `AGENTS.md`, with `CLAUDE.md` an identical copy.

## Next step

1. Redesign the UI to the updated `DESIGN.md`: multi-accent palette, web
   fonts, gradients and elevation, gamification, an overall progress score.
2. Bring `docs/ai-boundaries.md`, `docs/sources.md` and `docs/status.md` in
   line with `AGENTS.md`; they still describe code-only grading and
   owner-only licences. Tests that pin those claims need the same update.
3. Code still pins Python and `estnltk` (`.python-version`, `Dockerfile`,
   CI, `requirements.txt`); `AGENTS.md` says to track the latest stable.

## Uncommitted / undecided

- Untracked, not committed: `.claude/agents/`, `.claude/skills/`,
  `.claude/settings.local.json`, `.github/agents/`, `.github/hooks/`,
  `.github/skills/`.

## Blockers

- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer
  (it then falls back to `AGENTS.md`).
