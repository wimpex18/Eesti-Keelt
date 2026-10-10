# S8: the session, Täna and Haiku in the app

Current task: ADR-0009's session and next task. Backend done and tested:
`eesti/session.py` (seven steps, rotation, next task, hint, words, placement),
`eesti/api/session.py` (step content with keys withheld, first-attempt-only
answers, goal, placement, writing checklist, Miks?, rule question, HARNO
descriptor feedback), `eesti/tutor.py` (explanation languages, `ask_rule`,
`descriptor_feedback`), `tests/test_session.py`.

Next step: the screens — Täna (`path.js`), the session (`session.js`),
onboarding (`onboarding.js`), the rule page's question box (`lesson.js`);
then the journeys at 390 and 1280 px, DESIGN.md and the docs.

Outside the S8 file table (say so in the PR): `eesti/api/__init__.py`
(router), `eesti/evidence.py` (registers `session`), `docs/identity.md`
(routes), `tests/test_missing_content.py` (sweep value).

Uncommitted: none after this commit. Blockers: none.
