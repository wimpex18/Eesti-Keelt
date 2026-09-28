# Independent state backup

The Durable Objects are the live source of truth, but they share the Cloudflare
account's failure boundary. This job runs on the home Mac, pulls every permanent
account and evidence log over a dedicated read-only endpoint, verifies each
non-empty log by rebuilding its projections twice, and only then writes an
AES-256-GCM encrypted `.ekb` file outside the repository. The AES key is wrapped
with a local RSA-OAEP public key. Plaintext is never written as a backup file.

Guests are deliberately absent: their state is temporary. Caches, corpus,
device push subscriptions and current lockouts are also absent. The account
credentials and evidence logs are sufficient to recover sign-in and learner
state; browsers subscribe again and the app rebuilds projections and caches.

## One-time installation on the Mac

Choose a directory outside Cloudflare and outside this repository, ideally a
private encrypted disk or separately protected sync account:

```bash
zsh deploy/backup/install.sh \
  https://YOUR-WORKER-HOST \
  /absolute/path/to/private/off-account/Eesti-Keelt
```

The installer creates `~/.eesti-backup/private.pem`, its public key and a random
read-only token. It never prints the token. Put the same token in the Worker:

```bash
npx wrangler secret put BACKUP_TOKEN < ~/.eesti-backup/backup-token
launchctl kickstart -k gui/$(id -u)/ee.eestikeelt.backup
```

Inspect `~/.eesti-backup/backup.log`, `backup.error.log` and `last-success`. A
successful line contains `"backed_up":true`. launchd repeats the same pull,
decrypt and replay test daily at 03:20; a failed run also raises a local macOS
notification. Keep `private.pem` separately from the backup destination; losing
it makes the encrypted files unrecoverable. Do not copy `backup-token` or the
private key into the repository, Cloudflare, chat, or a shared environment.

## Verify and rehearse

Verification decrypts the selected file and replays every non-empty learner log
twice in isolated temporary databases. It does not contact or modify production:

```bash
node deploy/backup-state.mjs verify \
  /absolute/path/to/eesti-keelt-TIMESTAMP.ekb \
  --private-key ~/.eesti-backup/private.pem

node deploy/backup-state.mjs restore \
  /absolute/path/to/eesti-keelt-TIMESTAMP.ekb \
  --private-key ~/.eesti-backup/private.pem
```

Run the first command after installation and monthly thereafter. The second is
the restore command's default dry run and should report `"dry_run":true`.

## Disaster restore

1. Deploy the same Worker code and Durable Object migration in the replacement
   Cloudflare account. Configure normal app secrets, but do not open the app to
   learners yet.
2. Generate a new random restore token locally and set it only for this window:

   ```bash
   RESTORE_TOKEN="$(node -e 'process.stdout.write(require("node:crypto").randomBytes(32).toString("base64"))')"
   export RESTORE_TOKEN
   print -rn -- "$RESTORE_TOKEN" | npx wrangler secret put RESTORE_TOKEN
   ```

3. Run the dry run above, then apply to the replacement Worker:

   ```bash
   node deploy/backup-state.mjs restore \
     /absolute/path/to/eesti-keelt-TIMESTAMP.ekb \
     --private-key ~/.eesti-backup/private.pem \
     --url https://REPLACEMENT-WORKER-HOST --apply
   ```

4. Run the same command again. A safe completed restore reports zero added
   accounts and events. Conflicting event history is rejected; a live history
   that already extends the backup is never truncated.
5. Delete the powerful temporary secret, unset it locally, sign in, and run the
   deep smoke workflow before reopening access:

   ```bash
   npx wrangler secret delete RESTORE_TOKEN
   unset RESTORE_TOKEN
   ```

`BACKUP_TOKEN` cannot restore. `RESTORE_TOKEN` cannot export and should not exist
during normal operation.
