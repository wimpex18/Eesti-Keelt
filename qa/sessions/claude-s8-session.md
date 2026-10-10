# S8: the session, Täna and Haiku in the app

Current task: PR #139 [S8] waits for the owner's merge. Built: `eesti/session.py`,
`eesti/api/session.py`, `eesti/web/js/session.js`, Täna (`path.js`),
onboarding, Haiku's *Miks?*, *Küsi* and HARNO-descriptor comments
(`eesti/tutor.py`, shown by `eesti/web/js/modeltext.js` in the session, the
mock exam's writing review and Rääkimine), Profiil's explanation-language
switch, DESIGN.md's rhythm, Täna, session and keyboard search sections.

Follow-ups for R3 to fold in:
- The owner (11 Oct) finds the item formats generic (gap, choice rows,
  "Kuula ja vali: ____") and the names generic; both are in S11's brief, with
  `qa/naming.md` as the naming proposal (15 open questions for the owner).
  S4 should key labels by stable id.
- The session's words step uses EVS phrases (dictionary fragments, not
  always level-checked); the unit's own checked material could supply them.
- Peata keeps progress per step in `localStorage`; a cleared browser restarts
  the step (attempts already recorded stay).
- Text injection in the iOS simulator drops focus; type with its on-screen
  keys (tap the keys) to check a field there.

Owner operations: none new. Uncommitted: none after the commit. No secrets.
