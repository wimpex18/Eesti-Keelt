# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

PR #65 (`exam/p3-exam-domain`) carries P3, P4 and the P4 gaps:

- P3: HARNO's spec and sittings as data, the sitting as a `goal-set` event
  with `.ics`, `Proovieksam` (one part or all four on the clock), test-out;
- P4: per-correction provenance, the bounded tutor, the engine registry, a
  daily budget per lane, JSON request logs, per-class eval;
- ADR-0002 (`docs/adr/`): one tutor boundary — the writing check, the
  transcript check, translation, explanations and `Vestlus` (a model plays
  the paired-exam partner, capped at 8 turns, never scoring) all go through
  `eesti/tutor.py`.

## Next step

1. The user merges #65. Nothing new is needed in Cloud Shell.
2. P5 (plan): an ASR eval set (about 100 of the owner's own utterances,
   hand-transcribed, kept out of git), then a TalTech Whisper trial against
   Workers AI; TTS caching off the ephemeral disk (R2 or GCS); the speaking
   evidence model (completion, fluency, ASR uncertainty).

## Deferred on purpose (one learner)

- A Durable Object per identity; `DELETE /api/me`; a nightly log backup;
  the FSRS optimiser (after about 1 000 reviews).

## Blockers

- TartuNLP GEC backend (UT cluster) answers 500 after 60 s. The lane is kept;
  recheck `cli eval --provider tartunlp` in a few days.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
