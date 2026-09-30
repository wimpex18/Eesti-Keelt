# Handoff

Current task: Laudtee identity, ready for PR review.
Branch: `codex/laudtee-identity`, against `main`.

Laudtee names the app; Eesti keel · A2/B1 describes its subject.
One original three-plank SVG supplies header, browser, Apple/PWA and social art.
The 900 ms phone-only passage is inlined before paint, with no extra fetch.
Reduced motion, desktop/tablet and restored documents open directly.
The Worker supplies the public origin for social image metadata.
Artwork rebuild: `.venv/bin/python deploy/build-brand.py`; see `docs/brand.md`.

Verification: 2,491 Python tests passed (1 skip); 189 browser journeys passed
(3 viewport skips); 7 Worker tests, typecheck and Wrangler dry-run passed.
All tabs inspected at desktop, phone, landscape and tablet sizes in both themes.
Independent reviewer scored the startup fix resolved (`ship`).

Next: user review/merge the identity PR, then run deep smoke after automated
origin and Worker deployment. Production has not changed in this branch.
Uncommitted paths: none after this commit. No code blockers.
