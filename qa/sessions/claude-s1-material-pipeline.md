# S1 material pipeline — `claude/s1-material-pipeline`

Task: the material pipeline of ADR-0009 (`qa/opus-sessions.md`, S1). Built and
tested; spec in `docs/material.md`.

State: `eesti/material/` (schema, gates, blind, store, stats),
`eesti/cli/material.py` (`cli material schema|check|blind|build|stats`),
`eesti/api/reports.py` (`/api/material/units/{unit_id}`, `/answer`, `/report`),
tests `tests/test_material*.py` with a hand-written unit-4 fixture. Shared
files touched add-only: `eesti/cli/__init__.py`, `eesti/api/__init__.py`,
`eesti/licences.py` (`grove-material`), `docs/identity.md`, `docs/sources.md`,
`docs/status.md` (one row).

Next step: owner merges; S2 drafts into `content/material/` and runs
`cli material check`, then `cli material blind` (needs `ANTHROPIC_API_KEY`).

Follow-ups (outside S1's files):
- `cli push-content` (`eesti/cli/ops.py`) should run `cli material build`
  before uploading, or content.db ships without the checked material.
- `/api/read/questions/{item_id}` (`eesti/api/library.py`) offers model-written
  questions for any library text, `mat:` items included; it should serve the
  material's own checked questions instead.
- The unit page (S8) shows `/api/material/units/{unit_id}` with the label,
  off-list glosses and a *Teata veast* button.
- Context-only gaps (the object's case after negation) need a code trigger.

Uncommitted paths: none after the commit. Blockers: none. No secrets used.
