# S10 — `claude/s10-tokens-shell`

Task: Migration steps 1 and 2 of `DESIGN.md`: the Interlinear tokens and the
app shell. PR #134.

State: `eesti/web/app.css` reads only the roles (both themes, contrast,
reduced motion, forced colours); forbidden decoration is gone. The shell has
a sidebar (a 96px rail on tablets), a phone header with Veel and Profiil, a
dock of Täna and the four skills, an action bar for a screen's `data-primary`
and a task state (`data-dock-task` or the keyboard up) that rides on the
keyboard. `interlinear()` and `.il` are built, on no screen yet. Journeys
cover focus against the dock (three sizes, keyboard stub in both orders), the
tab row at 390/320 px in three languages, the sheets and the interlinear word;
checked by hand on the iOS 27 simulator too. Differences from the spec and
the device findings: `docs/design-research.md` ("Tokens and shell as built").

Next step: the owner merges; then S3 and S9 (step 4). Also on this branch at
the owner's request: `qa/competitor-review.md` and session S11 (after R4).

Follow-ups:
- S8: mark the session's one primary `data-primary` and its awaiting item
  `data-dock-task`; place *Peata* in the header; use `interlinear()` for the
  revealed word; build the desktop sticky action row.
- S3, S9: the rule page and the word card on `.il` and `dialog.sheet`.
- Changed outside S10's list because Migration asks it: `DESIGN.md` "Status
  of this record", `docs/status.md`, `docs/brand.md`, `docs/app-structure.md`,
  `PRODUCT.md` (one status sentence), `.claude/rules/web.md`; `md()` in
  `eesti/web/js/core.js`.

Uncommitted paths: none after the commit. Blockers: none. No secrets used.
