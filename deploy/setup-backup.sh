#!/usr/bin/env bash
# Give the nightly learner backup somewhere to land. Run in Google Cloud Shell.
#
#   bash deploy/setup-backup.sh
#   BUCKET=my-name RETAIN_DAYS=365 bash deploy/setup-backup.sh
#
# The Worker's nightly cron sends each permanent account's event log from its
# Durable Object to the origin, which replays it strictly and writes it here
# (`eesti/backup.py`). That puts a copy outside the Cloudflare account.
#
# What this sets up, and why:
#
#   - a private bucket in the service's region (uniform access, public access
#     prevented) whose objects are deleted after RETAIN_DAYS (default 180);
#   - roles/storage.objectCreator on that bucket for the Cloud Run service
#     account, and nothing else: the origin can add a copy but not read,
#     overwrite or delete one. Project-wide roles the account already holds
#     still apply, so they are listed below;
#   - EESTI_BACKUP_BUCKET on the service (this starts a new revision).
#
# No key is created: the origin uses its own identity from the metadata server.
# Safe to re-run.
set -euo pipefail

# shellcheck source=deploy/_service.sh
. "$(dirname "$0")/_service.sh"
find_service
PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
BUCKET="${BUCKET:-${PROJECT}-grove-backups}"
RETAIN_DAYS="${RETAIN_DAYS:-180}"
echo "==> $SERVICE in $REGION; bucket gs://$BUCKET"

if gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
  echo "    bucket exists"
else
  echo "==> Creating the bucket"
  gcloud storage buckets create "gs://$BUCKET" --location "$REGION" \
    --uniform-bucket-level-access --public-access-prevention
fi

echo "==> Deleting copies older than $RETAIN_DAYS days"
LIFECYCLE="$(mktemp)"
trap 'rm -f "$LIFECYCLE"' EXIT
printf '{"rule":[{"action":{"type":"Delete"},"condition":{"age":%d}}]}\n' \
  "$RETAIN_DAYS" > "$LIFECYCLE"
gcloud storage buckets update "gs://$BUCKET" --lifecycle-file="$LIFECYCLE" >/dev/null

SA="$(gcloud run services describe "$SERVICE" --region "$REGION" \
      --format='value(spec.template.spec.serviceAccountName)' 2>/dev/null || true)"
if [ -z "$SA" ]; then
  NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
  SA="${NUMBER}-compute@developer.gserviceaccount.com"
  echo "    the service runs as the default compute account: $SA"
fi

echo "==> Letting $SA add objects, and only that"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member="serviceAccount:$SA" --role=roles/storage.objectCreator >/dev/null

ROLES="$(gcloud projects get-iam-policy "$PROJECT" --flatten=bindings \
  --filter="bindings.members:serviceAccount:$SA" \
  --format='value(bindings.role)' 2>/dev/null || true)"
if [ -n "$ROLES" ]; then
  echo "    NOTE: project-wide roles of $SA also apply to this bucket:"
  sed 's/^/      /' <<<"$ROLES"
  echo "    A broad one (roles/editor) lets the origin delete copies too; a"
  echo "    dedicated service account without it keeps them out of its reach."
fi

echo "==> Pointing the service at the bucket (this starts a new revision)"
gcloud run services update "$SERVICE" --region "$REGION" --quiet \
  --update-env-vars "EESTI_BACKUP_BUCKET=$BUCKET" >/dev/null

cat <<NEXT

Done. The next nightly run (01:37 UTC) writes events/<account>/YYYY/MM/DD/*.jsonl.gz.
To check a copy yourself, in a trusted terminal:

  gcloud storage ls -r gs://$BUCKET/events/owner/ | tail -1
  gcloud storage cp gs://$BUCKET/events/owner/…/….jsonl.gz /private/path/
  python -m eesti.cli verify-backup /private/path/….jsonl.gz
NEXT
