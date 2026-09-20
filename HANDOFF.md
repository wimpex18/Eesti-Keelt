# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

PR #65 (`exam/p3-exam-domain`) carries P3–P6, HARNO's own tasks read in the
app, and now ADR-0004: a model writes the reading questions, the text keys
them, code grades them (`eesti/comprehension.py`, `Lugemine → Küsimused`).
`comprehension` events are the first practice the `lugemine` skill floor ever
counted.

## Recently fixed, worth knowing

- The browser suite had been failing since structured logging landed: the
  fixture gave uvicorn an unread `stdout=PIPE`, the buffer filled and the
  server stopped answering. It goes to a file now; 123 passed.
- HTTPS verifies against certifi (`eesti/tls.py`). Before that `arhiiv.eki.ee`
  would not verify here, so `cli rections` had never run and the whole
  `rektsioon` topic refused to generate. EVKK and both ERR feeds import now.

## Next step

1. The user merges #65; then in Cloud Shell: `bash deploy/check-service.sh`,
   `bash deploy/push-audio.sh`. `data/exam/` is not on the deployment yet —
   decide whether to mount it beside the audio bucket.
2. P5 finish: record ~100 utterances into `data/eval/asr/`, `cli eval --suite
   asr`, then trial TalTech verbatim Whisper against Workers AI.
3. P6 leftovers: Web Push (not started), FSRS optimiser (needs ~1 000 reviews;
   `review.db` has 0). Ekilex examples are done.

## Blockers

- TartuNLP GEC answers 500 after 60 s; recheck `cli eval --provider tartunlp`.
- Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
