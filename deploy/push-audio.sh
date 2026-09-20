#!/usr/bin/env bash
#
# Put EKI's recordings where the deployment can read them.
#
#   bash deploy/push-audio.sh            # upload and mount
#   bash deploy/push-audio.sh --check    # say what is there now
#
# `data/audio.db` is about 270 MB: too big for the image (every build would
# carry it) and far too big for the Durable Object snapshot, which exists for a
# learner's progress. Cloud Storage holds it instead, mounted read-only into the
# container, so the app opens it as an ordinary file and the Worker's edge cache
# keeps whatever is actually played.
#
# Costs at this size: a few cents a month of storage, and reads in the same
# region as the service.
#
# Run this in Google Cloud Shell with `data/audio.db` uploaded, or locally with
# `gcloud` signed in. Re-running replaces the file; the service is updated only
# when the mount is missing.
set -euo pipefail

BUCKET_SUFFIX="eesti-keelt-audio"
MOUNT="/mnt/audio"
VOLUME="eki-audio"

# shellcheck source=deploy/_service.sh
. "$(dirname "$0")/_service.sh"
find_service

PROJECT="$(gcloud config get-value project 2>/dev/null)"
BUCKET="${PROJECT}-${BUCKET_SUFFIX}"

if [ "${1:-}" = "--check" ]; then
  echo "bucket: gs://$BUCKET"
  gcloud storage ls "gs://$BUCKET/audio.db" 2>/dev/null \
    || echo "  (nothing uploaded yet)"
  gcloud run services describe "$SERVICE" --region "$REGION" \
    --format='value(spec.template.spec.volumes)' 2>/dev/null \
    | grep -q "$BUCKET" && echo "mount: present" || echo "mount: absent"
  exit 0
fi

AUDIO="${AUDIO_DB:-data/audio.db}"
[ -f "$AUDIO" ] || { echo "ERROR: $AUDIO not found. Import it first:" >&2
  echo "  python -m eesti.cli import-haaldused <folder> --index <index>" >&2
  exit 1; }

echo "==> Bucket gs://$BUCKET"
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --location "$REGION" \
       --uniform-bucket-level-access

echo "==> Uploading $(du -h "$AUDIO" | cut -f1)"
gcloud storage cp "$AUDIO" "gs://$BUCKET/audio.db"

if gcloud run services describe "$SERVICE" --region "$REGION" \
     --format='value(spec.template.spec.volumes)' 2>/dev/null | grep -q "$BUCKET"; then
  echo "==> Mount already in place; the new file is picked up on the next request"
  exit 0
fi

echo "==> Mounting it read-only at $MOUNT"
gcloud run services update "$SERVICE" --region "$REGION" --quiet \
  --add-volume "name=$VOLUME,type=cloud-storage,bucket=$BUCKET,readonly=true" \
  --add-volume-mount "volume=$VOLUME,mount-path=$MOUNT" \
  --update-env-vars "EESTI_AUDIO_DB=$MOUNT/audio.db" \
  >/dev/null

echo "Done. /api/pronounce now answers on the deployment;"
echo "check with: bash deploy/push-audio.sh --check"
