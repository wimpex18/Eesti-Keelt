# Handoff

## Current task
PR #66 merged into `main` at `26ae1f7`. Cloud Run revision
`eesti-keelt-00077-n7t` has `max-instances=1` and configured EKI/HARNO mounts.
Deep smoke [35910679079](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35910679079)
passed Access/origin guards, current image, reference data, `llm:workers-ai`
grammar, Ekilex and reading links. Workers AI GPT-OSS-120B remains automatic
hosted grammar/tutor with deterministic fallback; Cloudflare is production ASR;
others are eval-only. Branch smoke
[35913162942](https://github.com/wimpex18/Eesti-Keelt/actions/runs/35913162942) read 8,520 EKI forms but the deployed A2 catalogue has no downloaded-file metadata. The owner verified a sample PDF object in GCS, `EESTI_EXAM_DIR=/mnt/exam` and the `harno-exam` mount at `/mnt/exam`.

Chrome on the owner's Mac subscribed to reminders on 2026-09-23; browser
permission is granted and the page says `включены`. Delivery is pending.
Private export `~/Documents/Eesti-Keelt-Private-Backup/eesti-keelt-events-2026-09-23T2246.jsonl`
passed `cli verify-backup` (9 events); it excludes push subscriptions and audio.

PR #67 extends local-only `Hindamiskomplekt` for question answers and tentative
ASR drafts, discloses audio destinations, and checks production exam/audio
reads. Practice audio stays unsaved; prompts and ASR are never truth. Local
suite: 2210 passed; browser journeys: 133 passed, 5 skipped.

## Exact next step
Confirm the deployed catalogue's source/format/URL via the branch smoke probe.
PR #67 derives HARNO file paths from the original URL when the catalogue predates
the mount; verify after owner merge and Cloud Build with deep smoke on `main`.
Confirm actual Chrome reminder delivery at the next eligible hour outside 22:00–08:00.

## Blockers and working tree
Exam runtime access, push delivery and learner audio are pending; state copying is asynchronous.
