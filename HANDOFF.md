# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

PR #65 (`exam/p3-exam-domain`) carries P3, P4, ADR-0002, P5 and P6, and now
HARNO's own past tasks as in-app material: `cli harvest-exam --download`
fetches the exam board's PDFs and listening audio into `data/exam/`
(git-ignored, private study only), a PDF's text becomes the item's body, and
`Eksam` opens the task under the line that names it — text read on the page,
recording played there, file one click away (`/api/exam/file`,
`/api/exam/text`). A task not downloaded still links out to harno.ee.

## EKI audio

`data/audio.db` holds 8 520 word forms and 456 read sentences imported from
`arhiiv.eki.ee/litsents` (270 MB, A1–B1). Re-import with
`cli import-haaldused data/raw/eki-audio/wav --index .../soundpack.txt` and
`cli import-konekorpus data/raw/eki-audio/kylli`. On the deployment it is a
Cloud Storage bucket mounted read-only: `bash deploy/push-audio.sh` (Cloud
Shell), `--check` to see what is there.

## Next step

1. The user merges #65; then in Cloud Shell: `bash deploy/check-service.sh`
   and `bash deploy/push-audio.sh`. `data/exam/` is not on the deployment —
   decide whether to mount it beside the audio bucket or keep it local.
2. To finish P5: record about 100 short utterances into `data/eval/asr/`,
   run `cli eval --suite asr`, then trial TalTech's
   `whisper-large-v3-turbo-et-verbatim-2604` against Workers AI.
3. P6 leftovers (optional): Web Push, Ekilex collocations, FSRS optimiser.

## Blockers

- TartuNLP GEC backend answers 500 after 60 s. The lane is kept; recheck
  `cli eval --provider tartunlp` in a few days.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
