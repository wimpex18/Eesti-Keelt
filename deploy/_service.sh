# Find the Cloud Run service, and say what went wrong when it cannot be found.
#
# Sourced by set-llm-key.sh, push-content.sh and reset-progress.sh, which all
# opened with the same six lines:
#
#   LINE="$(gcloud run services list --format='...' 2>/dev/null | head -1)"
#   [ -n "$LINE" ] || { echo "ERROR: no Cloud Run service..." >&2; exit 1; }
#
# Under `set -euo pipefail` **that guard cannot fire.** A failing `gcloud` makes
# the pipeline fail, `pipefail` propagates it to the assignment, and `set -e`
# kills the script at that line — before the `[ -n ... ]` runs. Its stderr went
# to /dev/null, so the whole run produced *no output at all* and exit 1:
#
#   wimpex18@cloudshell:~/Eesti-Keelt$ bash deploy/set-llm-key.sh HF_TOKEN
#   wimpex18@cloudshell:~/Eesti-Keelt$
#
# Reported as "it didn't ask for the token". The error message was written, was
# correct, and was unreachable in exactly the case it existed for.
#
# `check-service.sh` never had this: it reads through `mapfile < <(...)`, whose
# failure does not trip `set -e`, and it checks the project first. `setup.sh`
# never had it either — it writes `|| true`. Two of five were right, which is
# why this is one function now rather than a fourth copy.

find_service() {
  command -v gcloud >/dev/null || {
    echo "ERROR: run this in Cloud Shell." >&2; exit 1; }

  # The project first, because "no service" and "no project" need different
  # actions and the second is much the commoner. Same check, same wording, as
  # check-service.sh.
  local project
  project="$(gcloud config get-value project 2>/dev/null || true)"
  [ -n "$project" ] && [ "$project" != "(unset)" ] || {
    echo "ERROR: no project selected. Pick one:" >&2
    gcloud projects list --format='value(projectId,name)' >&2
    echo "Then: gcloud config set project PROJECT_ID" >&2
    exit 1
  }

  # gcloud's stderr is kept and shown. Discarding it is what made the failure
  # silent; `|| true` is what lets the guard below run at all.
  local err line
  err="$(mktemp)"
  line="$(gcloud run services list \
    --format='value(metadata.name,metadata.labels."cloud.googleapis.com/location")' \
    2>"$err" | head -1 || true)"
  if [ -z "$line" ]; then
    echo "ERROR: no Cloud Run service found in project $project." >&2
    if [ -s "$err" ]; then
      echo "       gcloud said:" >&2
      sed 's/^/         /' "$err" >&2
    fi
    rm -f "$err"
    exit 1
  fi
  rm -f "$err"

  SERVICE="$(awk '{print $1}' <<<"$line")"
  REGION="$(awk '{print $2}' <<<"$line")"
}
