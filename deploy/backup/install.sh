#!/bin/zsh
set -euo pipefail

if (( $# != 2 )); then
  print -u2 -- "Usage: $0 https://app.example /absolute/off-account/backup-directory"
  exit 2
fi

URL="${1%/}"
DESTINATION="${2:A}"
SCRIPT_DIR="${0:A:h}"
ROOT="${SCRIPT_DIR:h:h}"
STATE_DIR="${EESTI_BACKUP_STATE:-$HOME/.eesti-backup}"
PLIST="$HOME/Library/LaunchAgents/ee.eestikeelt.backup.plist"
LABEL="ee.eestikeelt.backup"
NODE="$(command -v node || true)"

[[ "$URL" == https://* ]] || { print -u2 -- "The app URL must use HTTPS"; exit 2; }
[[ -n "$NODE" ]] || { print -u2 -- "Node.js is required"; exit 2; }
[[ "$DESTINATION" == /* ]] || { print -u2 -- "The destination must be absolute"; exit 2; }
[[ "$DESTINATION" != "$ROOT"* ]] || {
  print -u2 -- "Choose a destination outside the repository and hosting account"
  exit 2
}

umask 077
mkdir -p "$STATE_DIR" "$DESTINATION" "${PLIST:h}"
chmod 700 "$STATE_DIR" "$DESTINATION"

if [[ -e "$STATE_DIR/public.pem" || -e "$STATE_DIR/private.pem" ]]; then
  [[ -r "$STATE_DIR/public.pem" && -r "$STATE_DIR/private.pem" ]] || {
    print -u2 -- "Only one backup key exists; repair the key pair before installing"
    exit 1
  }
else
  "$NODE" "$ROOT/deploy/backup-state.mjs" keygen \
    --public "$STATE_DIR/public.pem" --private "$STATE_DIR/private.pem"
fi

if [[ ! -e "$STATE_DIR/backup-token" ]]; then
  "$NODE" -e 'process.stdout.write(require("node:crypto").randomBytes(32).toString("base64"))' \
    > "$STATE_DIR/backup-token"
fi
chmod 600 "$STATE_DIR/backup-token" "$STATE_DIR/private.pem" "$STATE_DIR/public.pem"
print -rn -- "$URL" > "$STATE_DIR/url"
print -rn -- "$DESTINATION" > "$STATE_DIR/destination"
print -rn -- "$NODE" > "$STATE_DIR/node"

"$NODE" "$ROOT/deploy/backup-state.mjs" self-test >/dev/null

rm -f "$PLIST"
plutil -create xml1 "$PLIST"
plutil -insert Label -string "$LABEL" "$PLIST"
plutil -insert ProgramArguments -array "$PLIST"
plutil -insert ProgramArguments.0 -string "$ROOT/deploy/backup/run.sh" "$PLIST"
plutil -insert StartCalendarInterval -dictionary "$PLIST"
plutil -insert StartCalendarInterval.Hour -integer 3 "$PLIST"
plutil -insert StartCalendarInterval.Minute -integer 20 "$PLIST"
plutil -insert StandardOutPath -string "$STATE_DIR/backup.log" "$PLIST"
plutil -insert StandardErrorPath -string "$STATE_DIR/backup.error.log" "$PLIST"
plutil -insert ProcessType -string Background "$PLIST"
chmod 600 "$PLIST"

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

print -- "Installed a daily 03:20 backup to: $DESTINATION"
print -- "Encryption private key (keep separate): $STATE_DIR/private.pem"
print -- "Before the first run, configure the Worker's matching read-only secret:"
print -- "  cd ${(q)ROOT} && npx wrangler secret put BACKUP_TOKEN < ${(q)STATE_DIR}/backup-token"
print -- "Then test one real pull:"
print -- "  launchctl kickstart -k gui/$(id -u)/$LABEL"
