# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

PR #65 (`exam/p3-exam-domain`) carries P3, P4, ADR-0002 and P5:

- P5: `cli eval --suite asr` scores recognisers on the owner's own recordings
  (WER, CER, latency, and the false-accept rate that decides the choice);
  `/api/speak` has a cacheable GET form and the Worker keeps the audio at the
  edge, so a cold start no longer re-synthesises every sentence; a spoken
  answer is recorded with what code can measure (answered, words, pace, the
  share of words Vabamorf rejects) and readiness reports that practice
  without judging the part.

## Next step

1. The user merges #65.
2. To finish P5: record about 100 short utterances into `data/eval/asr/`
   (a `.wav` and a `.txt` each; add a `.said` where a word was deliberately
   said wrong), run `cli eval --suite asr`, then trial TalTech's
   `whisper-large-v3-turbo-et-verbatim-2604` against Workers AI and commit
   the results table before any swap.
3. P6 (plan, all optional): Web Push, offline practice packs, Ekilex
   collocations, the FSRS optimiser.

## Deferred on purpose (one learner)

- A Durable Object per identity; `DELETE /api/me`; a nightly log backup.

## Blockers

- TartuNLP GEC backend (UT cluster) answers 500 after 60 s. The lane is kept;
  recheck `cli eval --provider tartunlp` in a few days.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
