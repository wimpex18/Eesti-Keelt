# Handoff

Current task: Estep identity, phone navigation and Linear tracking policy.
Branch: `codex/laudtee-identity`; PR: #95 against `main`.

Estep (Estonian + step) names the app; the larger header has no subject subtitle.
One stepped-E vector supplies browser, Apple/PWA and social artwork.
Phones have a 900 ms point-climbing splash with early dismissal and motion/
restoration exclusions. Desktop and tablet open directly.
Phone skill and mode rows support hold/drag preview and release to select,
including edge scrolling and cancellation. Profile/login replaces transparency.
The footer explains the name, shows the current year and retains sources.
AGENTS.md includes the user's durable-backlog Linear tracking policy.
Artwork rebuild: `.venv/bin/python deploy/build-brand.py`; see `docs/brand.md`.

Verification: 2,491 Python tests passed (1 skip); typecheck and 7 Worker tests
passed. The Worker dry-run passed. 202 browser journeys passed (4 skips).
All 11 tabs inspected at desktop, phone, landscape and tablet sizes in both
themes. Independent scoped finish review: ship; raster provenance complete.

Next: user review/merge PR #95, then run deep smoke after automated origin
and Worker deployment.
Uncommitted paths: none after this commit.
No code blockers; production has not changed in this branch.
