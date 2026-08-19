#!/usr/bin/env bash
#
# Send a harvested reading library to the deployment. Run in Google Cloud Shell.
#
#   bash deploy/push-content.sh path/to/content.db
#
# Why this exists rather than "copy the file into the container": Cloud Run's
# disk is ephemeral, so a file copied in by hand is gone at the next cold start.
# And the library cannot ride along inside the image, because ERR transcripts
# are © ERR and Selges keeles carries no reuse grant -- putting them in an image
# built from a public repository would be redistribution.
#
# Why it targets Cloud Run rather than the Worker: Cloudflare Access guards the
# Worker, and Access is an interactive login that a script cannot satisfy. The
# origin is guarded by PROXY_TOKEN instead, which a script can send. The Worker
# then archives the corpus from the origin and pushes it into every container
# that starts afterwards.
#
# You never see or type either token: they are read straight out of the running
# Cloud Run service, which is the only place they need to exist.
set -euo pipefail

DB="${1:-data/content.db}"
[ -f "$DB" ] || { echo "ERROR: $DB does not exist." >&2; exit 1; }

command -v gcloud >/dev/null || { echo "ERROR: run this in Cloud Shell." >&2; exit 1; }

echo "==> Finding the Cloud Run service"
LINE="$(gcloud run services list \
  --format='value(metadata.name,metadata.labels."cloud.googleapis.com/location")' \
  2>/dev/null | head -1)"
[ -n "$LINE" ] || { echo "ERROR: no Cloud Run service. Is the project set?" >&2; exit 1; }
SERVICE="$(awk '{print $1}' <<<"$LINE")"
REGION="$(awk '{print $2}' <<<"$LINE")"
echo "    $SERVICE in $REGION"

echo "==> Reading the service's own tokens"
read_env() {
  gcloud run services describe "$SERVICE" --region "$REGION" \
    --format="value(spec.template.spec.containers[0].env.filter(\"name:$1\").extract(value))" \
    2>/dev/null | tr -d '[]'
}
STATE_TOKEN="$(read_env STATE_TOKEN)"
PROXY_TOKEN="$(read_env PROXY_TOKEN)"
[ -n "$STATE_TOKEN" ] && [ -n "$PROXY_TOKEN" ] || {
  echo "ERROR: the service has no STATE_TOKEN/PROXY_TOKEN. Run deploy/setup.sh first." >&2
  exit 1
}

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" \
        --format='value(status.url)')"

echo "==> Pushing $DB"
STATE_TOKEN="$STATE_TOKEN" PROXY_TOKEN="$PROXY_TOKEN" \
  python3 -m eesti.cli push-content --url "$URL" --database "$DB"

echo
echo "Open the app and check the reading list. If it is still empty, the Worker"
echo "has not looked yet -- it archives on the next cold start, or you can force"
echo "one by deploying a new revision."
