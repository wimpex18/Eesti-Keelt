# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

PR #65 (`exam/p3-exam-domain`) now carries P3 **and** P4:

- P3: HARNO's spec and sittings as data, the sitting as a `goal-set` event
  with `.ics`, `Proovieksam` (one part or all four on the exam's clock,
  writing graded on length plus the deterministic checks), test-out;
- P4: per-correction provenance (`deterministic` / `model+verified` /
  `model-only`, only the first two reach the error log), the bounded tutor
  (`Selgita`, grounded in EKK and Vabamorf, dropped if it invents a form),
  the engine registry (version, quota, what leaves the device), a daily
  budget per lane, JSON request logs, and an attested eval track with
  per-class recall and precision.

## Next step

1. The user merges #65. Nothing new is needed in Cloud Shell.
2. What P4 still lacks: the tutor has no conversation intent (roleplay), and
   `/api/check` still answers separately rather than through `tutor.py`.
3. P5 (plan): the ASR eval set and a possible TalTech Whisper swap, TTS
   caching off the ephemeral disk, the speaking evidence model.

## Deferred on purpose (one learner)

- A Durable Object per identity; `DELETE /api/me`; a nightly log backup;
  the FSRS optimiser (after about 1 000 reviews).

## Blockers

- TartuNLP GEC backend (UT cluster) answers 500 after 60 s. The lane is kept;
  recheck `cli eval --provider tartunlp` in a few days.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
