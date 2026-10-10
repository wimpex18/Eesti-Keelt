# S7 design spec, rename to Klint — `claude/s7-design-spec`

Task: the redesign spec (S7), then at the owner's request the follow-ups:
rename Grove → Klint, the default explanation language, a session for
`eesti/web/app.css`, Kodu → Täna. PR #131.

State: `DESIGN.md` is the target spec, "Interlinear" (form name under the
Estonian word from code; spruce ink on birch; one fixed primary; three-state
phone dock; seven-step session line; motion, contrast, focus, iOS, explanation
languages, migration). `docs/design-research.md` holds the audit, the
references and the decisions, including the name. The app is Klint: page
title, metadata, manifest, header, reminders, profile copy, docs and qa notes;
the mark is an underlined K and the brand assets are rebuilt in spruce and
birch (`deploy/build-brand.py`). Identifiers keep "grove" (`grove-material`,
the Worker). Home's label is Täna. `PRODUCT.md` states the language default
(first of uk, ru, en from the system; else en; a saved choice wins).
`qa/opus-sessions.md` adds S7R (the spec review) and S10 (tokens and shell,
owns `app.css`); S3, S4, S8, S9 briefs point at DESIGN.md and the language rule.

Next step: run S7R in a new session; then the owner merges; then S10.

Follow-ups:
- Owner: Business Register and trademark search for "Klint", then buy klint.ee.
- S10: tokens, shell, manifest/theme colours, offline page, focus journey.
- S4: implement the language default on web; the iOS app later.

Uncommitted paths: none after the commit. Blockers: none. No secrets used.
