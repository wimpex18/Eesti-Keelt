# Handoff

Current state for the next session, Claude Code or Codex. Overwrite, never
append; at most 30 lines.

## Task in flight

PR #65 (`exam/p3-exam-domain`) now carries all of P3–P6:

- the official material read in the app (HARNO's PDFs and audio, EIS's
  interactive tasks with their own recordings);
- ADR-0004 — a model writes the reading questions, the text keys them, code
  grades them (`Lugemine → Küsimused`);
- reminders (`eesti/reminders.py` decides, the Worker's cron sends, VAPID +
  RFC 8291; `Edenemine → Meeldetuletused`);
- `cli optimise-review` — FSRS fitted to this learner once there are ~1 000
  reviews, recorded as a `fsrs-parameters` event (`review.db` has 0 so far).

## After the merge, in Cloud Shell

```bash
bash deploy/check-service.sh        # max-instances 1
bash deploy/push-audio.sh           # EKI recordings (270 MB)
bash deploy/push-exam.sh            # HARNO task files (124 MB)
bash deploy/push-content.sh data/content.db   # library incl. task text
python -m eesti.cli push-keys       # first, on this machine
bash deploy/set-push-keys.sh        # then reminders can be switched on
```

## Next

1. P5 finish: record ~100 utterances into `data/eval/asr/`, `cli eval --suite
   asr`, then trial TalTech verbatim Whisper against Workers AI.
2. Recheck `cli eval --provider tartunlp` — its backend answered 500 for days.
3. Delete `CLAUDE.md` once Claude for Mac bundles Claude Code 2.1.277 or newer.
