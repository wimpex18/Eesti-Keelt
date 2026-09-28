# Handoff

Current task: make permanent-account state acknowledgements durable and retries safe.

Branch: `codex/durable-event-ack`; PR #94 is open against `main`.

Implemented: successful origin API responses wait for the learner Durable Object to copy through `x-events-seq`; failed copy/boot changes re-run restoration and return an explicit 503 instead of acknowledging vulnerable work. Practice and review retries preserve one answer, latency and event id; FSRS applies each review event exactly once. Snapshots remain asynchronous and guests unchanged.

Verification: 2,495 tests passed, 1 skipped; 173 browser journeys passed, 3 skipped in Chromium and WebKit; the focused failure retry passed on desktop and phone. TypeScript, JS syntax, `git diff --check` and Wrangler dry-run pass.

Next: review GitHub checks and merge PR #94. Independent off-account backups remain separate follow-up work.

Uncommitted paths: none.

Blockers: none.
