# Handoff

## Current task
PR #66 merged into `main` at `26ae1f7`. Cloud Run revision
`eesti-keelt-00077-n7t` has `max-instances=1` and EKI audio/HARNO exam mounts.
Deep smoke [35910679079](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35910679079)
passed after mounting: Access/origin guards, current image, reference data,
`llm:workers-ai` grammar, Ekilex and reading links. Workers AI GPT-OSS-120B
remains automatic hosted grammar/tutor with deterministic fallback; Cloudflare
remains production ASR. Other candidates are eval-only.

Chrome on the owner's Mac subscribed to reminders on 2026-09-23; browser
permission is granted and the page says `включены`. Delivery is pending.
Private export `~/Documents/Eesti-Keelt-Private-Backup/eesti-keelt-events-2026-09-23T2246.jsonl`
passed `cli verify-backup` (9 events); it excludes push subscriptions and audio.

PR #67 extends local-only `Hindamiskomplekt` for question answers and tentative
ASR drafts, discloses audio destinations, and checks production exam/audio
reads. Practice audio stays unsaved; prompts and ASR are never truth. Local
suite: 2210 passed; browser journeys: 133 passed, 5 skipped.

## Exact next step
Push PR #67 and run branch smoke against production for mounted-file reads.
After owner merge and Cloud Build, run deep smoke on `main`. At the next eligible
hourly reminder outside 22:00–08:00, confirm Chrome delivery with the owner.
Collect manually listened-to clips under ignored `data/eval/asr/` for paired ASR.

## Blockers and working tree
Push delivery and learner audio are pending; state replication is asynchronous.
PR #67 files are being committed together; no other changes are intended.
