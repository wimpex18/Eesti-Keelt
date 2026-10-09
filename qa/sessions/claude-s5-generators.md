# claude/s5-generators — S5, generators the units lack

**Task.** The generators `docs/course-structure.md` named as missing: negation
beyond present and past, modal + infinitive, `tulevik`, conjugation and
imperative gaps in EVS phrases, the missing question-word cues; a check for
units 17 and 28.

**State.** Done; fast suite green (3066 passed); question-cue, credit and unit
journeys pass on both engines. GENERATOR_VERSION 6.

**Next step.** Owner merges. After the merge, `cli import-evs` once in any
checkout used for local serving (the Docker build already runs it): cues for
`kellega`, `kellele`, `kui palju` live in `evs_question`.

**Follow-ups (not done).**
- `kelle` stays cue-less: EVS's seven questions with it share no Russian
  opening. VES (Russian–Estonian) might attest `чей` → `kelle`; not downloaded.
- `liitsonad` (unit 28) and `uhendverbid` still have no generator.
- Negated past impersonal (*ei tehtud*) is not drilled: EKK M 99 as read here
  names only *ei elata* and *ei ole elatud*, and EVS has one such phrase.
- `tingiv` and `umbisikuline` keep their bleached frames beside the new
  sources; their EVS phrase gaps (non-negated) are not built.

**Outside the brief, changed.** `docs/sources.md` (one count, 8 → 11
question-word cues): `tests/test_question_cues.py` checks it.

**Uncommitted.** None. **Blockers.** None.
