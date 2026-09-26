# Handoff

Current task: production QA fixes on `codex/production-qa`, ready for review.
All ten routes checked in Chrome at 1440×900 and 393×852, light and dark,
including route reload and browser history. Local fixes also checked at
402×874, 874×402 and 744×1133 with touch emulation.

Fixes cover touch targets, accessible bounded word cards, language and engine
attribution, outlined writing input, in-app official material/video, milestone
wrapping, correct empty-state heading levels, graded microphone locking and
stable checkpoint regeneration.
Generator version is 2; signed answers remain authoritative for grading.
Review follow-ups: official rows share `library.official_availability`; a
catalogued link-out stays one in Lugemine/Kuulamine and `audio_url` rows stay in
the app. `principal_forms` draws candidates from `words` only, so a seed
regenerates whatever the form cache holds. Reader words are one roving tab
stop. Impeccable ignores: CSS lines annotated in place; index.html page-scan
rules (no line or value to match) are ignored for that file only.

Validation: `pytest tests/ -n auto` and `npm run typecheck` pass; browser
journeys pass in Chromium (the video test now serves its own catalogue).
Production queue was empty; saved-progress journeys used isolated local state.

Next step: user reviews draft PR #89 from `codex/production-qa`.
Uncommitted paths: none. Blockers: none.
