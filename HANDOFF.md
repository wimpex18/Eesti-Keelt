# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

Architecture strategy approved on 2026-09-19 (the plan is kept outside the
repo; its decisions are summarised here). P0 "safety" is on branch
`fix/p0-safety`:

- snapshot guard by boot id and learner rows;
- 503 for writes before restore; `max-instances 1`;
- read-aloud no longer primes Whisper;
- checkpoint result endpoint;
- `Topic.reference` fallback;
- rule on attempts and review cards;
- TartuNLP lane in the GEC eval;
- docs aligned to ADR-1 (code grades; model scores are advisory evidence).

## Next step

1. After merge: in Cloud Shell, run `bash deploy/check-service.sh`, apply the
   maximum-instances fix it prints (`setup.sh` also sets it), then run the
   `deploy.yml` workflow for the Worker.
2. P1: an append-only event log in a per-learner Durable Object
   (`idFromName(access email)`), server-signed item refs, FSRS review logs and
   auto-rating, projections replacing `progress/review/vocab.db`.

## Uncommitted / undecided

- 8 files under `eesti/web/` (`app.css`, `chrome/core/listen/reading/review/
  speak/vocab.js`) hold the user's own uncommitted redesign work. They are not
  part of this branch.
- Local agent, skill, hook and settings folders under `.claude` and `.github`
  are untracked.

## Blockers

- TartuNLP GEC sends nothing within 60 s (2026-09-19); its eval cannot score.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
