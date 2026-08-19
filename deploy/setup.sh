#!/usr/bin/env bash
#
# One-time wiring between Cloud Run, GitHub and Cloudflare.
#
# Run this in **Google Cloud Shell** (the terminal icon in the Cloud Console).
# Cloud Shell is already signed in to your Google account, so nothing here needs
# a Google password, and it has gcloud, openssl and gh pre-installed.
#
#   git clone https://github.com/wimpex18/Eesti-Keelt.git
#   cd Eesti-Keelt
#   bash deploy/setup.sh
#
# What it does, and why each part exists:
#
#   1. Invents PROXY_TOKEN and STATE_TOKEN. These are not accounts you sign up
#      for -- they are two random strings whose only job is to be known in two
#      places and nowhere else. PROXY_TOKEN proves a request came through the
#      Cloudflare Worker, so the public run.app URL is not a way around
#      Cloudflare Access. STATE_TOKEN guards the endpoints that export and
#      import your progress.
#
#   2. Puts them on the Cloud Run service, because the app reads them from its
#      environment. Without them the app answers 503 on the snapshot endpoints
#      and reports origin_guarded=false, which means the front door is the only
#      lock on a house with two doors.
#
#   3. Puts the same two, plus the Cloud Run URL it looks up for you, into this
#      repository's GitHub Actions secrets, because that is where the deploy
#      workflow reads them from.
#
# Nothing is printed. Nothing is written to a file. Re-running it rotates both
# tokens in both places at once, which is the only safe way to rotate them.
set -euo pipefail

REPO="wimpex18/Eesti-Keelt"
SERVICE="${SERVICE:-eesti-keelt}"
REGION="${REGION:-europe-north1}"

fail() { echo "ERROR: $*" >&2; exit 1; }

command -v gcloud >/dev/null || fail "gcloud not found. Run this in Cloud Shell."
command -v gh     >/dev/null || fail "gh not found. Run this in Cloud Shell."

echo "==> Finding the Cloud Run service '$SERVICE' in '$REGION'"
# `|| true` so a wrong region gives the sentence below rather than a stack trace.
URL="$(gcloud run services describe "$SERVICE" --region "$REGION" \
        --format='value(status.url)' 2>/dev/null || true)"
[ -n "$URL" ] || fail "No service '$SERVICE' in '$REGION'.
  List what you have:  gcloud run services list
  Then re-run with the right names, e.g.
    SERVICE=my-service REGION=europe-west1 bash deploy/setup.sh"
echo "    $URL"

echo "==> Checking you are signed in to GitHub"
gh auth status >/dev/null 2>&1 || {
  echo "    Not signed in. Opening the login flow -- choose HTTPS, and"
  echo "    authenticate in a browser."
  gh auth login
}

echo "==> Generating two random secrets"
PROXY_TOKEN="$(openssl rand -hex 32)"
STATE_TOKEN="$(openssl rand -hex 32)"

echo "==> Setting them on the Cloud Run service (this starts a new revision)"
gcloud run services update "$SERVICE" --region "$REGION" --quiet \
  --update-env-vars "PROXY_TOKEN=$PROXY_TOKEN,STATE_TOKEN=$STATE_TOKEN" \
  >/dev/null

echo "==> Storing the same values as GitHub Actions secrets"
# Via stdin: an argument would put the secret in the process table and in your
# shell history.
printf '%s' "$PROXY_TOKEN" | gh secret set PROXY_TOKEN   --repo "$REPO"
printf '%s' "$STATE_TOKEN" | gh secret set STATE_TOKEN   --repo "$REPO"
printf '%s' "$URL"         | gh secret set CLOUD_RUN_URL --repo "$REPO"

echo "==> Verifying the app came up with the guard on"
# The one check worth making: the app should now refuse a request that has no
# token and accept one that has it. If this passes, the second door is shut.
code_without="$(curl -s -o /dev/null -w '%{http_code}' "$URL/api/health")"
code_with="$(curl -s -o /dev/null -w '%{http_code}' \
             -H "x-proxy-token: $PROXY_TOKEN" "$URL/api/health")"
if [ "$code_without" = "403" ] && [ "$code_with" = "200" ]; then
  echo "    OK: open request refused (403), authorised request served (200)."
else
  echo "    Not there yet: unauthorised=$code_without authorised=$code_with"
  echo "    A new revision can take a minute. Re-check with:"
  echo "      curl -o /dev/null -w '%{http_code}\n' $URL/api/health"
  echo "    Expect 403. Anything else means the guard is not active yet."
fi

cat <<'NEXT'

Done. Two things are left, and both are in the Cloudflare dashboard because
both create credentials, which is not something a script should do for you.

  1. My Profile -> API Tokens -> Create Token -> "Edit Cloudflare Workers"
     template -> Continue -> Create. Copy the token; it is shown once.
     Copy your Account ID from the right-hand side of the Workers overview.

     Then, back here:
       gh secret set CLOUDFLARE_API_TOKEN  --repo wimpex18/Eesti-Keelt
       gh secret set CLOUDFLARE_ACCOUNT_ID --repo wimpex18/Eesti-Keelt

     Each waits for you to paste the value and press Ctrl-D.

  2. Merge the open pull request. The deploy workflow runs on its own, and
     when it finishes, turn on Access:
       Workers & Pages -> eesti-keelt -> Settings -> Domains & Routes
       -> Enable Cloudflare Access -> allowed email: your own.
NEXT
