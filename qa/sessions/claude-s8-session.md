# S8: the session, Täna and Haiku in the app

Current task: PR #139 [S8] waits for the owner's merge. Built: `eesti/session.py`,
`eesti/api/session.py`, `eesti/web/js/session.js`, Täna (`path.js`),
onboarding, Haiku's *Miks?*, *Küsi* and HARNO-descriptor comments
(`eesti/tutor.py`), DESIGN.md's rhythm, Täna and session sections.

Follow-ups for R3 to fold in:
- The owner (11 Oct) finds the item formats generic (gap, choice rows,
  "Kuula ja vali: ____") and the names generic; both are in S11's brief, with
  `qa/naming.md` as the naming proposal. S4 should key labels by stable id.
- The model's HARNO-descriptor comments are in the session only; the mock
  exam's writing review (`eesti/web/js/mock.js`) and Rääkimine could call the
  same `/api/session/feedback`.
- Explanation language is set in onboarding; Profile has no switch yet (S4).
- Sõnastik with the real iOS keyboard: rows not confirmed (simulator text
  injection drops focus); `docs/status.md` says so.
- The session's words step uses EVS phrases (dictionary fragments, not
  always level-checked); the unit's own checked material could supply them.
- Peata keeps progress per step in `localStorage`; a cleared browser restarts
  the step (attempts already recorded stay).

Owner operations: none new. Uncommitted: none after the commit. No secrets.
