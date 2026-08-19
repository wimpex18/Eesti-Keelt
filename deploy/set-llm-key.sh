#!/usr/bin/env bash
#
# Give the Cloud Run service a grammar-explanation key. Run in Cloud Shell.
#
#   bash deploy/set-llm-key.sh
#
# Why this exists as its own script: the key is read by
# eesti/providers/llm.py, which runs in the *container*, not in the Worker.
# It was being deployed as a Worker secret, where nothing reads it -- so the
# grammar checker stayed in offline mode (object-case candidates and typos, but
# no corrections) while the key sat somewhere useless. That is all of the risk
# of holding a credential and none of the benefit.
#
# The value is read from the terminal without echoing and passed to gcloud on
# stdin, so it never reaches your shell history or the process table. It is
# never printed.
set -euo pipefail

VAR="${1:-OPENROUTER_API_KEY}"
case "$VAR" in
  OPENROUTER_API_KEY|GROQ_API_KEY|ANTHROPIC_API_KEY|CLOUDFLARE_API_TOKEN) ;;
  *) echo "ERROR: $VAR is not a key this app reads. See eesti/env.py." >&2
     exit 1 ;;
esac

command -v gcloud >/dev/null || { echo "ERROR: run this in Cloud Shell." >&2; exit 1; }

LINE="$(gcloud run services list \
  --format='value(metadata.name,metadata.labels."cloud.googleapis.com/location")' \
  2>/dev/null | head -1)"
[ -n "$LINE" ] || { echo "ERROR: no Cloud Run service. Is the project set?" >&2; exit 1; }
SERVICE="$(awk '{print $1}' <<<"$LINE")"
REGION="$(awk '{print $2}' <<<"$LINE")"
echo "==> $SERVICE in $REGION"

printf 'Paste %s (input is hidden), then press Enter: ' "$VAR"
read -rs VALUE
echo
[ -n "$VALUE" ] || { echo "Nothing entered; no change made." >&2; exit 1; }

echo "==> Setting it (this starts a new revision)"
gcloud run services update "$SERVICE" --region "$REGION" --quiet \
  --update-env-vars "^@^$VAR=$VALUE" >/dev/null
unset VALUE

# Confirm rather than assume. This script used to print "Done" and tell you to
# go and look -- and a run of it left the service without the variable, which
# nobody noticed until the deployment was asked directly weeks later. Read the
# *names* back off the service that is actually serving traffic; the value is
# never fetched, so nothing secret is printed or stored.
echo "==> Verifying"
NAMES="$(gcloud run services describe "$SERVICE" --region "$REGION" \
  --format='value(spec.template.spec.containers[0].env.name)' 2>/dev/null)"
if ! grep -qw "$VAR" <<<"$NAMES"; then
  echo "ERROR: $VAR is not on $SERVICE after the update." >&2
  echo "       Variables present: ${NAMES:-none}" >&2
  echo "       If this project has more than one Cloud Run service, this" >&2
  echo "       script took the first one. Check: gcloud run services list" >&2
  exit 1
fi

REV="$(gcloud run services describe "$SERVICE" --region "$REGION" \
        --format='value(status.latestReadyRevisionName)')"
SERVING="$(gcloud run services describe "$SERVICE" --region "$REGION" \
        --format='value(status.traffic[0].revisionName)' 2>/dev/null)"
URL="$(gcloud run services describe "$SERVICE" --region "$REGION" \
        --format='value(status.url)')"

echo "$VAR is set on $SERVICE (revision $REV)"
if [ -n "$SERVING" ] && [ "$SERVING" != "$REV" ]; then
  echo
  echo "WARNING: traffic is still on $SERVING, not $REV."
  echo "         The variable will not take effect until traffic moves:"
  echo "         gcloud run services update-traffic $SERVICE \\"
  echo "           --region $REGION --to-latest"
fi
echo
echo "The app should stop answering 'Офлайн-режим' and start naming an engine."
echo "Service: $URL"
