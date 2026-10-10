# S7 design and motion spec — `claude/s7-design-spec`

Task: the design and motion spec for the redesign, documents only
(`qa/opus-sessions.md`, S7). Written.

State: `DESIGN.md` is the target spec, "Interlinear": the Estonian form with
its form name under it from code; spruce ink on birch ground; one primary per
screen in a phone action bar or a desktop sticky row; a three-state phone dock;
seven-step session line under Õpi / Harjuta / Kontrolli; motion inventory with
reduced-motion and forced-colours fallbacks; WCAG 2.2 AA contrast table; focus
rules against the dock; iOS 26 mapping; migration order and token map.
`docs/design-research.md` holds the audit of today's screens (390 and 1280 px,
light and dark), the October 2026 references and the decisions.

Next step: the reviewer session scores it; then the owner merges.

Follow-ups (outside S7's files; for the PR and later sessions):
- No session owns `eesti/web/app.css`; migration step 1 (tokens) needs one.
- When a step ships, update `PRODUCT.md` (visual system line),
  `.claude/rules/web.md` (Practice rhythm sentence), `docs/status.md`
  (Interface), `docs/brand.md` and `deploy/build-brand.py` (tile colours).
- S8: Täna, the session state machine (retry with hint), the interlinear word.
- S3: Reegel as a page with sources at the top and the form switch.
- A focus-versus-dock journey in `tests/test_e2e_journeys.py`.
- Tab labels "Kodu" → "Täna" is a copy change for S8.

Uncommitted paths: none after the commit. Blockers: none. No secrets used.
