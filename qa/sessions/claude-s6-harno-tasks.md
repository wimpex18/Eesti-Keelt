# S6 HARNO task types — `claude/s6-harno-tasks`

Task: HARNO B1 reading and listening task types keyed by code, A2 after
(`qa/opus-sessions.md`, S6). Built and tested.

State: `eesti/harnotasks.py` (types `B1-ku1/ku3/lu3/lu4`, `A2-ku1/ku3/lu5`,
generators, grading), `eesti/mock.py` (`lugemine:harno` / `lugemine:3`
sections, practice not counted as a sitting, `retests` 1/3/6 days),
`eesti/web/js/mock.js` (HARNO blocks, two-voice playback heard twice, review,
*Harjuta*, *Kordamine*), `tests/test_harnotasks.py`. Shared, add-only:
`eesti/api/exam.py` (`?format=harno` on the existing mock routes, `retests`
in `/api/mock/{level}`; no new route, so `docs/identity.md` is untouched).
`docs/status.md`: the Mock row.

Next step: owner merges. Reading 4 (`B1-lu4`) builds once S2 checks in texts.

Follow-ups (outside S6's files):
- `readiness.py`: show HARNO task types covered per part (ADR-0009).
- `itemref.GENERATOR_VERSION`: mock refs now regenerate HARNO sections by part
  string; no bump was needed for existing refs, but S5's file owns it.
- Reading 1–2 and listening 2 and 4 are not generated: they need
  comprehension questions, which need checked material (S2) or HARNO's own.

Uncommitted paths: none after the commit. Blockers: none. No secrets used.
