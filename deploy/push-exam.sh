#!/usr/bin/env bash
#
# Put the exam board's own task files where the deployment can read them.
#
#   bash deploy/push-exam.sh            # upload and mount
#   bash deploy/push-exam.sh --check    # say what is there now
#
# `data/exam/` is about 130 MB of HARNO's task PDFs and listening recordings,
# downloaded for private study (`cli harvest-exam --download`). The extracted
# *text* travels with the library (`cli push-content`), so a task can be read on
# the deployment either way; these are the files themselves — above all the
# listening recordings, which is the half a phone cannot get from the text.
#
# Same shape as `push-audio.sh`: a Cloud Storage bucket mounted read-only, so
# the app opens the files as ordinary paths. Without the mount the app says a
# task is not downloaded and links out to harno.ee, which is correct rather than
# broken.
#
# Costs at this size: a few cents a month.
#
# Run this in Google Cloud Shell with `data/exam/` uploaded, or locally with
# `gcloud` signed in. Re-running syncs; the service is updated only when the
# mount is missing.
set -euo pipefail

BUCKET_SUFFIX="eesti-keelt-exam"
MOUNT="/mnt/exam"
VOLUME="harno-exam"

# shellcheck source=deploy/_service.sh
. "$(dirname "$0")/_service.sh"
find_service

PROJECT="$(gcloud config get-value project 2>/dev/null)"
BUCKET="${PROJECT}-${BUCKET_SUFFIX}"

if [ "${1:-}" = "--check" ]; then
  echo "bucket: gs://$BUCKET"
  gcloud storage ls "gs://$BUCKET/**" 2>/dev/null | head -5 \
    || echo "  (nothing uploaded yet)"
  echo "files: $(gcloud storage ls "gs://$BUCKET/**" 2>/dev/null | wc -l | tr -d ' ')"
  gcloud run services describe "$SERVICE" --region "$REGION" \
    --format='value(spec.template.spec.volumes)' 2>/dev/null \
    | grep -q "$BUCKET" && echo "mount: present" || echo "mount: absent"
  exit 0
fi

EXAM="${EXAM_DIR:-data/exam}"
[ -d "$EXAM" ] || { echo "ERROR: $EXAM not found. Download the material first:" >&2
  echo "  python -m eesti.cli harvest-exam --levels A2,B1 --download" >&2
  exit 1; }

echo "==> Bucket gs://$BUCKET"
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --location "$REGION" \
       --uniform-bucket-level-access

echo "==> Syncing $(du -sh "$EXAM" | cut -f1) from $EXAM"
gcloud storage rsync --recursive --delete-unmatched-destination-objects \
  "$EXAM" "gs://$BUCKET"

if gcloud run services describe "$SERVICE" --region "$REGION" \
     --format='value(spec.template.spec.volumes)' 2>/dev/null | grep -q "$BUCKET"; then
  echo "==> Mount already in place; new files are picked up on the next request"
  exit 0
fi

echo "==> Mounting it read-only at $MOUNT"
gcloud run services update "$SERVICE" --region "$REGION" --quiet \
  --add-volume "name=$VOLUME,type=cloud-storage,bucket=$BUCKET,readonly=true" \
  --add-volume-mount "volume=$VOLUME,mount-path=$MOUNT" \
  --update-env-vars "EESTI_EXAM_DIR=$MOUNT" \
  >/dev/null

echo "Done. Exam tasks now open in the app on the deployment;"
echo "check with: bash deploy/push-exam.sh --check"
