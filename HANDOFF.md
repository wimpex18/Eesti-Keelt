# Handoff

Workstream S1 (Oct 2026 review, epic DEV-35): correctness defects, one PR per
issue in order DEV-49 → DEV-50 → DEV-51 → DEV-53 → DEV-52. Owner merges.

Current task: DEV-49 EVS glosses, branch claude/dev-49-evs-glosses (PR open).
- `eesti/evs.py`: homographs chosen by EKI's level list (POS + corpus count);
  negation-only senses dropped when the first sense is ordinary.
- `cli import-evs` reads `A1A2B1.txt` beside the EVS file (`--levels`); the
  Docker build re-imports on merge, nothing to run by hand.
- Progress counter: glossed words out of ranked words, all offline sources.
- Known limits recorded in docs/status.md (väär, kord ordering).
Checks: 2552 passed/14 skipped with local data; journeys 205 passed/23 skipped.
Next: after merge, DEV-50 (writing checks: missing partitive objects, poodi,
Tallinas). Design notes: Vabamorf readings; flag sg-n-only nouns after 1st/2nd
person or negated transitive verbs; EVS `vrek` (что/кого) is the only offline
transitivity signal found; PSV rection too sparse.
Uncommitted: none after this commit. Worktree `data/*.db` are copied reference
DBs (git-ignored), not learner data.
Blockers: none. S2 (DEV-54) may touch `eesti/cloze.py`; later PR rebases.
