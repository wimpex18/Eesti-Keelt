#!/usr/bin/env bash
#
# Forget a topic's practice history on the deployment. Run in Cloud Shell.
#
#   bash deploy/reset-progress.sh kusisonad
#   bash deploy/reset-progress.sh --everything
#
# Targets the Cloud Run origin rather than the Worker, for the same reason
# push-content.sh does: Cloudflare Access is an interactive login and a script
# cannot satisfy one. Both tokens are read out of the running service, so you
# never see or type either.
set -euo pipefail

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "Usage: $0 <topic> | --everything" >&2; exit 1; }

command -v gcloud >/dev/null || { echo "ERROR: run this in Cloud Shell." >&2; exit 1; }

LINE="$(gcloud run services list \
  --format='value(metadata.name,metadata.labels."cloud.googleapis.com/location")' \
  2>/dev/null | head -1)"
[ -n "$LINE" ] || { echo "ERROR: no Cloud Run service. Is the project set?" >&2; exit 1; }
SERVICE="$(awk '{print $1}' <<<"$LINE")"
REGION="$(awk '{print $2}' <<<"$LINE")"

read_env() {
  gcloud run services describe "$SERVICE" --region "$REGION" \
    --format="value(spec.template.spec.containers[0].env.filter(\"name:$1\").extract(value))" \
    2>/dev/null | tr -d '[]'
}
STATE_TOKEN="$(read_env STATE_TOKEN)"
PROXY_TOKEN="$(read_env PROXY_TOKEN)"
URL="$(gcloud run services describe "$SERVICE" --region "$REGION" \
        --format='value(status.url)')"

if [ "$TARGET" = "--everything" ]; then
  printf 'This erases ALL practice history. Type ERASE to confirm: '
  read -r answer
  [ "$answer" = "ERASE" ] || { echo "Cancelled."; exit 1; }
  BODY='{"everything": true}'
  echo "==> Clearing everything"
else
  BODY="$(printf '{"topic": "%s"}' "$TARGET")"
  echo "==> Clearing topic '$TARGET'"
fi

curl -sS -X POST "$URL/api/progress/reset" \
  -H 'content-type: application/json' \
  -H "x-state-token: $STATE_TOKEN" \
  -H "x-proxy-token: $PROXY_TOKEN" \
  -d "$BODY"
echo
