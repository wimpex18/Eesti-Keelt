#!/usr/bin/env bash
# Say what the deployment is actually configured with. Run in Google Cloud
# Shell. Changes nothing.
#
#   bash deploy/check-service.sh
#
# A key set in the wrong place (e.g. on the Worker, where nothing reads it) has
# no visible symptom beyond corrections arriving without explanations. The smoke
# workflow asks the running app from outside; this script answers from the
# operator's side and names the service and revision.
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

  # The things whose absence is silent, and what each one costs.
  for pair in \
    "PROXY_TOKEN|the run.app URL answers the whole internet" \
    "CLOUDFLARE_API_TOKEN NVIDIA_API_KEY MISTRAL_API_KEY OPENROUTER_API_KEY|grammar has no explanations, so nothing reaches the Notion log" \
    "NOTION_TOKEN|confirmed errors queue locally and never push" \
    "EKILEX_API_KEY|the word card reads the third-party Sõnaveeb mirror instead of EKI's Ekilex API"
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

  # Learner state is SQLite on the instance's disk: a second instance records
  # answers into a copy the Worker's snapshot never sees.
  MAX="$(gcloud run services describe "$SERVICE" --region "$REGION" \
    --format='value(spec.template.metadata.annotations."autoscaling.knative.dev/maxScale")' \
    2>/dev/null)"
  if [ "$MAX" = "1" ]; then
    echo "   ok   max-instances 1"
  else
    echo "   WARNING: max-instances is ${MAX:-unset}; two instances split the learner's state."
    echo "            Cloud Console -> Cloud Run -> $SERVICE -> Edit & deploy new"
    echo "            revision -> Maximum number of instances: 1"
  fi

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
