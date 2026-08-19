#!/usr/bin/env bash
#
# Say what the deployment is actually configured with. Run in Google Cloud
# Shell. Changes nothing.
#
#   bash deploy/check-service.sh
#
# Why this exists: the grammar checker sat in offline mode for weeks because
# OPENROUTER_API_KEY was on the Worker, where nothing reads it. It was then set
# on Cloud Run -- and still was not there, which nobody could see, because the
# only symptom is corrections quietly arriving without explanations.
#
# The smoke workflow can now ask the running app the same question from
# outside. This script answers it from the operator's side, and it is the one
# that can tell you *which* service and *which* revision, which is where the
# discrepancy usually lives.
#
# Variable NAMES only. No value is ever fetched, printed, or written anywhere.
set -euo pipefail

command -v gcloud >/dev/null || { echo "ERROR: run this in Cloud Shell." >&2; exit 1; }

PROJECT="$(gcloud config get-value project 2>/dev/null)"
[ -n "$PROJECT" ] && [ "$PROJECT" != "(unset)" ] || {
  echo "ERROR: no project selected. Pick one:" >&2
  gcloud projects list --format='value(projectId,name)' >&2
  echo "Then: gcloud config set project PROJECT_ID" >&2
  exit 1
}
echo "project: $PROJECT"
echo

# Every service, not just the first: "the script took the first one" is itself
# a way this has gone wrong.
mapfile -t SERVICES < <(gcloud run services list \
  --format='value(metadata.name,metadata.labels."cloud.googleapis.com/location")' \
  2>/dev/null)
[ "${#SERVICES[@]}" -gt 0 ] || { echo "No Cloud Run services in $PROJECT." >&2; exit 1; }
[ "${#SERVICES[@]}" -eq 1 ] || echo "NOTE: ${#SERVICES[@]} services. Scripts that" \
  "take the first one may be targeting the wrong one."

for LINE in "${SERVICES[@]}"; do
  SERVICE="$(awk '{print $1}' <<<"$LINE")"
  REGION="$(awk '{print $2}' <<<"$LINE")"
  echo "── $SERVICE ($REGION)"

  NAMES="$(gcloud run services describe "$SERVICE" --region "$REGION" \
    --format='value(spec.template.spec.containers[0].env.name)' 2>/dev/null \
    | tr ';' ' ')"
  echo "   env: ${NAMES:-none}"

  # The four things whose absence is silent, and what each one costs.
  for pair in \
    "PROXY_TOKEN|the run.app URL answers the whole internet" \
    "OPENROUTER_API_KEY GROQ_API_KEY ANTHROPIC_API_KEY CLOUDFLARE_API_TOKEN|grammar has no explanations, so nothing reaches the Notion log" \
    "NOTION_TOKEN|confirmed errors queue locally and never push"
  do
    want="${pair%%|*}"; cost="${pair#*|}"
    found=""
    for v in $want; do
      grep -qw "$v" <<<"$NAMES" && { found="$v"; break; }
    done
    if [ -n "$found" ]; then
      printf '   ok   %s\n' "$found"
    else
      printf '   MISSING %s\n        -> %s\n' "$(awk '{print $1}' <<<"$want")" "$cost"
    fi
  done

  LATEST="$(gcloud run services describe "$SERVICE" --region "$REGION" \
             --format='value(status.latestReadyRevisionName)')"
  SERVING="$(gcloud run services describe "$SERVICE" --region "$REGION" \
             --format='value(status.traffic[0].revisionName)' 2>/dev/null)"
  if [ -n "$SERVING" ] && [ "$SERVING" != "$LATEST" ]; then
    echo "   WARNING: traffic is on $SERVING, newest ready is $LATEST."
    echo "            A variable set on the newest revision is not in effect:"
    echo "            gcloud run services update-traffic $SERVICE \\"
    echo "              --region $REGION --to-latest"
  else
    echo "   revision: ${SERVING:-$LATEST} (serving)"
  fi
  echo
done
