#!/usr/bin/env bash
# Send a harvested reading library to the deployment. Run in Google Cloud Shell.
#
#   bash deploy/push-content.sh path/to/content.db
#
# Cloud Run's disk is ephemeral, so a file copied in by hand is gone at the next
# cold start, and the library cannot ride in the image: ERR transcripts are
# © ERR and Selges keeles carries no reuse grant, and the image is built from a
# public repository.
#
# It targets Cloud Run rather than the Worker because Cloudflare Access is an
# interactive login a script cannot satisfy; the origin is guarded by
# PROXY_TOKEN, which a script can send. The Worker then archives the corpus from
# the origin and restores it into every container that starts afterwards.
#
# You never see or type either token: they are read straight out of the running
# Cloud Run service, which is the only place they need to exist.
set -euo pipefail

DB="${1:-data/content.db}"
[ -f "$DB" ] || { echo "ERROR: $DB does not exist." >&2; exit 1; }

# shellcheck source=deploy/_service.sh
. "$(dirname "$0")/_service.sh"
echo "==> Finding the Cloud Run service"
find_service
echo "    $SERVICE in $REGION"

echo "==> Reading the service's own tokens"
# Read as JSON and picked out by name, not with gcloud's projection DSL: the DSL
# form (`env.filter(...).extract(value)`) can return a non-empty but wrong value,
# which passes the emptiness check and fails later as an unexplained 403.
DESCRIBE="$(gcloud run services describe "$SERVICE" --region "$REGION" \
            --format=json 2>/dev/null)"
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
STATE_TOKEN="$(read_env STATE_TOKEN)"
PROXY_TOKEN="$(read_env PROXY_TOKEN)"
[ -n "$STATE_TOKEN" ] && [ -n "$PROXY_TOKEN" ] || {
  echo "ERROR: the service has no STATE_TOKEN/PROXY_TOKEN. Run deploy/setup.sh first." >&2
  exit 1
}

URL="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"]["url"])' \
       <<<"$DESCRIBE")"

# Pre-flight, before spending a megabyte on a request that may be refused.
# `/api/health` is cheap and behind the same guard, so a 403 here means the
# proxy token is wrong -- and says so, instead of the upload failing at the end
# with a message that does not name which of the two tokens was at fault.
echo "==> Checking the tokens are accepted"
CODE="$(curl -s -o /dev/null -w '%{http_code}' \
        -H "x-proxy-token: $PROXY_TOKEN" "$URL/api/health")"
case "$CODE" in
  200) echo "    origin accepts PROXY_TOKEN" ;;
  403) echo "ERROR: the origin refused PROXY_TOKEN." >&2
       echo "       The value on the service is not the one the app compares" >&2
       echo "       against. Re-set it on Cloud Run *and* on the Worker so the" >&2
       echo "       two match, then run this again:" >&2
       echo "         gcloud run services update $SERVICE --region $REGION \\" >&2
       echo "           --update-env-vars PROXY_TOKEN=\$(openssl rand -hex 32)" >&2
       echo "       and put the same value in the Worker secret PROXY_TOKEN." >&2
       exit 1 ;;
  *)   echo "ERROR: $URL/api/health answered $CODE, not 200." >&2; exit 1 ;;
esac

echo "==> Pushing $DB"
STATE_TOKEN="$STATE_TOKEN" PROXY_TOKEN="$PROXY_TOKEN" \
  python3 -m eesti.cli push-content --url "$URL" --database "$DB"

echo
echo "Open the app and check the reading list. If it is still empty, the Worker"
echo "has not looked yet -- it archives on the next cold start, or you can force"
echo "one by deploying a new revision."
