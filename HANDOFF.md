# Handoff

Current task: review workstream S4 (data safety, dependencies), Linear DEV-37
and DEV-39, as one PR; Litestream (DEV-43) waits until after 7–8 Nov.
Branch: claude/dev-37-dev-39-data-safety, merged with origin/main 4d6bf01.
Contains: DEV-37 items 1–7 (owner rebind, corpus revision, liveness, reminder
cron, ITEM_SECRET, guest allowances and sandboxes, nightly verified GCS copy);
DEV-39 (requirements.lock, python:3.14.8, weekly upgrade workflow, npm and
wrangler, compatibility_date 2026-10-01, pinned local ASR, install.sh as
updater); AGENTS.md: no new Linear issues, one open PR per session.
Checks: see the PR; local Docker build of the merged tree passed.
Next (owner): enable Settings → Actions → General → "Allow GitHub Actions to
create and approve pull requests"; merge; after the image is live, in Cloud
Shell run `bash deploy/set-item-secret.sh` and `bash deploy/setup-backup.sh`;
next morning verify one copy with `cli verify-backup`; on the Mac mini unpack
the new ZIP and run `zsh deploy/home-asr/install.sh`; deep smoke.
Waiting: Node 26 after 28 Oct 2026 (JS checks pass on 26.11.1); Python 3.15
until estnltk, python-crfsuite, pyahocorasick and httptools ship cp315 wheels.
Uncommitted task paths: none after this commit.
Blockers: none.
