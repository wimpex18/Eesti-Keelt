#!/usr/bin/env bash
# Give item tokens their own signing secret. Run in Google Cloud Shell.
#
#   bash deploy/set-item-secret.sh            # once: generate ITEM_SECRET if absent
#   bash deploy/set-item-secret.sh --rotate   # new ITEM_SECRET; the old one verifies
#
# Each drill item travels to the page with an HMAC token (`eesti/itemref.py`),
# and an answer queued offline is re-graded from it, possibly weeks later.
# Without ITEM_SECRET the tokens are signed with PROXY_TOKEN, so rotating the
# origin guard would turn every queued answer into a refusal.
#
# The app keeps accepting tokens signed with PROXY_TOKEN or STATE_TOKEN, so
# setting the secret invalidates nothing. `--rotate` moves the current value to
# ITEM_SECRET_PREVIOUS, which still verifies; rotate again only after queued
# answers have had time to arrive, because the value before that is dropped.
#
# Values are generated here and passed to gcloud without being printed or
# written to a file. Only variable names are read back.
set -euo pipefail

ROTATE=0
case "${1:-}" in
  "") ;;
  --rotate) ROTATE=1 ;;
  *) echo "Usage: bash deploy/set-item-secret.sh [--rotate]" >&2; exit 1 ;;
esac

command -v openssl >/dev/null || { echo "ERROR: openssl not found." >&2; exit 1; }

# shellcheck source=deploy/_service.sh
. "$(dirname "$0")/_service.sh"
find_service
echo "==> $SERVICE in $REGION"

DESCRIBE="$(gcloud run services describe "$SERVICE" --region "$REGION" \
            --format=json 2>/dev/null || true)"
[ -n "$DESCRIBE" ] || { echo "ERROR: could not describe $SERVICE." >&2; exit 1; }
read_env() {
  python3 -c '
import json, sys
name = sys.argv[1]
env = json.load(sys.stdin)["spec"]["template"]["spec"]["containers"][0].get("env", [])
for entry in env:
    if entry.get("name") == name:
        print(entry.get("value", ""))
        break
' "$1" <<<"$DESCRIBE"
}
CURRENT="$(read_env ITEM_SECRET)"

if [ -n "$CURRENT" ] && [ "$ROTATE" -eq 0 ]; then
  echo "ITEM_SECRET is already set; no change made. Use --rotate to replace it."
  exit 0
fi

NEW="$(openssl rand -hex 32)"
if [ "$ROTATE" -eq 1 ] && [ -n "$CURRENT" ]; then
  UPDATE="ITEM_SECRET=$NEW,ITEM_SECRET_PREVIOUS=$CURRENT"
  echo "==> Rotating (the current secret becomes ITEM_SECRET_PREVIOUS)"
else
  UPDATE="ITEM_SECRET=$NEW"
  echo "==> Setting ITEM_SECRET (this starts a new revision)"
fi
gcloud run services update "$SERVICE" --region "$REGION" --quiet \
  --update-env-vars "^@^${UPDATE//,/@}" >/dev/null
unset NEW CURRENT UPDATE DESCRIBE

echo "==> Verifying"
NAMES="$(gcloud run services describe "$SERVICE" --region "$REGION" \
  --format='value(spec.template.spec.containers[0].env.name)' 2>/dev/null || true)"
if ! grep -qw ITEM_SECRET <<<"$NAMES"; then
  echo "ERROR: ITEM_SECRET is not on $SERVICE after the update." >&2
  echo "       Variables present: ${NAMES:-none}" >&2
  exit 1
fi
echo "ITEM_SECRET is set on $SERVICE."
