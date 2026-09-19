# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

PR #64 (`fix/p0-safety`) carries P0 safety, the Neurotõlge est→est grammar
lane, the web redesign files with their test fixes, and P1:

- evidence log (`eesti/evidence.py`), with the learner DBs as projections;
- signed, regenerable item refs (`eesti/itemref.py`);
- FSRS auto-rating and review logs;
- the log in the Worker's Durable Object;
- `Minu andmed` export.

## Next step

1. After merge, in Cloud Shell: run `bash deploy/check-service.sh` and set
   maximum instances to 1 if it warns; then run `deploy.yml` for the Worker.
   The first restore backfills the log from the snapshot.
2. Remaining P1:
   - name the Durable Object per Access identity (still `singleton`; the
     origin is single-tenant);
   - `DELETE /api/me`;
   - a nightly log export to R2 or GCS;
   - the FSRS optimiser once there are about 1 000 reviews.
3. P2: concept representations and a coverage test, mastery decay and weak
   rules, the "Täna" planner, replay and similar-task endpoints.

## Uncommitted / undecided

- Local agent, skill, hook and settings folders under `.claude` and `.github`
  are untracked.

## Blockers

- TartuNLP GEC backend (UT cluster) answers 500 after 60 s. The lane is kept;
  recheck `cli eval --provider tartunlp` in a few days.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
