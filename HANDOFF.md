# Handoff

Current task: independent encrypted off-account backup and tested disaster restore; implementation complete.

Branch: `codex/durable-event-ack`; PR #94 is open against `main`.

Implemented: permanent-account responses wait for the Durable Object event copy; retries preserve one event and FSRS applies it once. A separate Mac job now pulls every account/log through a read-only token, encrypts with AES-GCM plus RSA-OAEP, decrypts and strictly replays the stored artifact before its atomic commit, and reports daily failure. Restore uses a separate temporary token, preflights paged logs, rejects divergence and only appends a missing suffix.

Verification: 2,503 tests passed, 1 skipped; backup pull/encryption/tamper/replay/dry-run tests pass; TypeScript, Node and zsh syntax, `git diff --check` and Wrangler dry-run pass. The earlier 173 browser journeys passed with 3 skips; this addition changes no web UI.

Next: merge and deploy PR #94, then follow `deploy/backup/README.md`: choose the external destination, install the launchd job, set `BACKUP_TOKEN`, kick-start one real pull and confirm `last-success`. Keep `RESTORE_TOKEN` unset outside a recovery.

Uncommitted paths: none after the pending commit.

Blockers: code has none. Off-account protection is not operational until the one-time destination and secret setup above.
