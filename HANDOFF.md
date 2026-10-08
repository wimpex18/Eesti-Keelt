# Handoff

Current task: review workstream S4 (data safety and dependencies), Linear
DEV-37 and DEV-39. Litestream (DEV-43) waits until after the 7–8 Nov sittings.
Branch: claude/dev-37-item-secret, from origin/main faa477d (DEV-37 item 6).
In this branch: item tokens verify against `ITEM_SECRET`,
`ITEM_SECRET_PREVIOUS`, `PROXY_TOKEN` and `STATE_TOKEN` and sign with the
first set of `ITEM_SECRET`/`PROXY_TOKEN`/`STATE_TOKEN`;
`deploy/set-item-secret.sh` sets or rotates it without printing values;
`check-service.sh` flags it missing.
Checks: Python 2528 passed/25 skipped (no local data).
Next: owner merges, waits for the image, then runs
`bash deploy/set-item-secret.sh` once in Cloud Shell (no Worker change).
Other S4 PRs: wimpex18/Eesti-Keelt#112 (DEV-37 items 2–5); dependency lock
(DEV-39) and nightly off-Cloudflare export (DEV-37 item 1, destination
awaits owner choice) follow.
Uncommitted task paths: none after this commit.
Blockers: none for this PR.
