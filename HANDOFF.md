# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

Branch `exam/p3-exam-domain` (PR not opened yet) carries P3:

- `eesti/exam.py`: HARNO's spec and sittings as data; the sitting is the
  learner's choice (`goal-set` event), drives the countdown and `.ics`;
- `eesti/mock.py`: `Proovieksam`, one part on the exam's clock, recorded as
  `exam-section` evidence that readiness counts;
- test-out from `Kogu rada` (`/api/testout/{topic}`), graded server-side.

## Next step

1. Open the PR; the user merges. Then, in Cloud Shell, nothing new is
   required: the image carries the change.
2. What P3 still lacks: the writing mock is graded only by word count (the
   writing check explains the rest), and no mock covers a whole sitting in
   one run.
3. P4 (plan): the bounded AI tutor, the 200-case GEC eval, per-correction
   provenance, the source registry as data, structured logging and budgets.

## Deferred on purpose (one learner)

- A Durable Object per identity; `DELETE /api/me`; a nightly log backup;
  the FSRS optimiser (after about 1 000 reviews).

## Blockers

- TartuNLP GEC backend (UT cluster) answers 500 after 60 s. The lane is kept;
  recheck `cli eval --provider tartunlp` in a few days.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
