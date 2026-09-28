#!/bin/zsh
set -euo pipefail

STATE_DIR="${EESTI_BACKUP_STATE:-$HOME/.eesti-backup}"
TOKEN_FILE="$STATE_DIR/backup-token"
URL_FILE="$STATE_DIR/url"
DESTINATION_FILE="$STATE_DIR/destination"
NODE_FILE="$STATE_DIR/node"
PUBLIC_KEY="$STATE_DIR/public.pem"
PRIVATE_KEY="$STATE_DIR/private.pem"

for file in "$TOKEN_FILE" "$URL_FILE" "$DESTINATION_FILE" "$NODE_FILE" \
    "$PUBLIC_KEY" "$PRIVATE_KEY"; do
  if [[ ! -r "$file" ]]; then
    print -u2 -- "Backup configuration is missing: $file"
    exit 1
  fi
done

BACKUP_TOKEN="$(<"$TOKEN_FILE")"
if (( ${#BACKUP_TOKEN} < 32 )); then
  print -u2 -- "Backup token is too short"
  exit 1
fi
export BACKUP_TOKEN

SCRIPT_DIR="${0:A:h}"
if RESULT="$("$(<"$NODE_FILE")" "$SCRIPT_DIR/../backup-state.mjs" backup \
    --url "$(<"$URL_FILE")" \
    --public-key "$PUBLIC_KEY" \
    --private-key "$PRIVATE_KEY" \
    --out "$(<"$DESTINATION_FILE")" 2>&1)"; then
  print -- "$RESULT"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$STATE_DIR/last-success"
else
  STATUS=$?
  print -u2 -- "$RESULT"
  /usr/bin/osascript -e \
    'display notification "Encrypted state backup failed; inspect ~/.eesti-backup/backup.error.log" with title "Eesti Keelt"' \
    >/dev/null 2>&1 || true
  exit "$STATUS"
fi
