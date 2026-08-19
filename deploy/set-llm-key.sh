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

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" \
        --format='value(status.url)')"
echo
echo "Done. Check it took effect by writing a sentence in the app: the check"
echo "should stop saying 'Офлайн-режим' and start naming an engine."
echo "Service: $URL"
