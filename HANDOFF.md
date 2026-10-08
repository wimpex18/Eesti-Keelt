# Handoff

Current task: review workstream S4 (data safety and dependencies), Linear
DEV-37 and DEV-39. Litestream (DEV-43) waits until after the 7–8 Nov sittings.
Branch: claude/dev-37-durable-object-defects, from origin/main faa477d.
In this branch (DEV-37 items 2–5): guests no longer rebind the owner object;
the archived corpus records its revision, so eviction or a cold restore does
not re-archive it; `/api/health?live=1` is the Worker's liveness probe and the
full report counts recordings once per file version; `/api/reminders` names
`next_check`, and the cron skips cold restores until then or new evidence.
Checks: Python 2529 passed/25 skipped (no local data), Worker 32 passed,
typecheck clean.
Rollout: the Worker and origin deploy independently; each side accepts the
other's old form (missing `live`, `revision` or `next_check` keeps old behaviour).
Next: owner reviews and merges; after deployment run smoke with `deep: true`.
Separate PRs follow: ITEM_SECRET (DEV-37 item 6), dependency lock (DEV-39),
nightly off-Cloudflare export (DEV-37 item 1, destination awaits owner choice).
Uncommitted task paths: none after this commit.
Blockers: none for this PR.
