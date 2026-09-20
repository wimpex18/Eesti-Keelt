#!/usr/bin/env bash
# Give the Worker the VAPID pair that signs reminders. Run in Cloud Shell.
#
#   python -m eesti.cli push-keys      # once, on your machine: writes .env
#   bash deploy/set-push-keys.sh       # here, with that .env present
#
# Reminders are sent by the Worker (`sendPush` in deploy/worker.ts), so the pair
# belongs to the Worker and nowhere else: on Cloud Run it would sit unread and
# no notification would ever be sent.
#
# Values are read from `.env` and passed to wrangler on stdin, so they never
# reach your shell history or the process table, and neither is printed.
set -euo pipefail

ENV_FILE="${1:-.env}"
[ -f "$ENV_FILE" ] || { echo "ERROR: $ENV_FILE not found. Run this first:" >&2
  echo "  python -m eesti.cli push-keys" >&2; exit 1; }

value() {
  # The last assignment wins, matching eesti/env.py.
  sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1
}

PUBLIC="$(value VAPID_PUBLIC_KEY)"
PRIVATE="$(value VAPID_PRIVATE_KEY)"
SUBJECT="$(value VAPID_SUBJECT)"
[ -n "$PUBLIC" ] && [ -n "$PRIVATE" ] || {
  echo "ERROR: $ENV_FILE has no VAPID pair. Run: python -m eesti.cli push-keys" >&2
  exit 1; }

put() { printf '%s' "$2" | npx wrangler secret put "$1"; }

echo "==> Pushing the VAPID pair to the Worker"
put VAPID_PUBLIC_KEY "$PUBLIC"
put VAPID_PRIVATE_KEY "$PRIVATE"
put VAPID_SUBJECT "${SUBJECT:-mailto:none@example.org}"

echo
echo "Done. Turn reminders on in the app: Eksam -> Edenemine -> Meeldetuletused."
echo "On iPhone that works only from the app added to the Home Screen (iOS 16.4+)."
