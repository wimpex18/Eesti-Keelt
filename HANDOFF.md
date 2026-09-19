# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

PR #64 (`fix/p0-safety`) carries:

- P0 safety; the Neurotõlge grammar lane; the web redesign files;
- P1: evidence log, signed item refs, FSRS auto-rating, log in the Durable
  Object, writing and speech evidence;
- a slimmer test suite (fast by default, `--browser` opt-in);
- P2: topic representations, weak rules and refresh (`learner.py`), and
  today's plan (`planning.py`, Rada's Täna).

## Next step

1. After merge, in Cloud Shell: run `bash deploy/check-service.sh` and set
   maximum instances to 1 if it warns; then run `deploy.yml` for the Worker.
2. P3 (before registration opens on 2027-01-01): ExamSpec and ExamSession data,
   a `goal_set` event replacing `readiness.TARGET`, timed mocks with section
   evidence, readiness v2, `.ics` reminders, a placement API.

## Deferred on purpose (one learner)

- A Durable Object per identity; `DELETE /api/me`; a nightly log backup;
  the FSRS optimiser (after about 1 000 reviews).

## Blockers

- TartuNLP GEC backend (UT cluster) answers 500 after 60 s. The lane is kept;
  recheck `cli eval --provider tartunlp` in a few days.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
