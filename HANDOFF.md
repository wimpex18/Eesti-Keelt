# Handoff

Current task: review workstream S4 (data safety, dependencies), Linear DEV-37
and DEV-39; Litestream (DEV-43) waits until after the 7–8 Nov sittings.
This note is identical on every S4 branch, so the PRs merge in any order.
Open PRs (owner merges; then deep smoke):
- #112 DEV-37 items 2–5: owner rebind, corpus revision, liveness, reminder cron.
- #113 DEV-37 items 6–7: ITEM_SECRET; guest allowances in the owner's
  snapshotted store; active sandboxes kept past the soft limit (hard 200).
- #116 DEV-39: requirements.lock, python:3.14.8, upgrade workflow, npm/wrangler,
  local ASR pins (Voxtral bench rerun).
- #118 DEV-37 item 1: nightly verified copy to GCS (stacked on #112).
- #119 AGENTS.md: no new Linear issues; follow-up goes in comments.
After merge (owner, Cloud Shell): enable Actions "create and approve pull
requests" (before #116); `bash deploy/set-item-secret.sh` (#113);
`bash deploy/setup-backup.sh` (#118), then verify a copy the next morning.
Waiting: Node 26 after 28 Oct 2026 (suite already passes on 26.11.1);
Python 3.15 until estnltk, python-crfsuite, pyahocorasick and httptools ship
cp315 wheels.
Uncommitted task paths: none after each branch's commit.
Blockers: none.
