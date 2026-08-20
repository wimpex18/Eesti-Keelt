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
#
# THIS IS NOT A DEPLOY COMMAND, and re-running it casually takes the app down.
#
# It writes the new tokens to Cloud Run and to GitHub Actions secrets. It does
# NOT write them to the Cloudflare Worker -- the Worker gets them from the
# `deploy` workflow, via `wrangler secret put`. So between rotating and that
# workflow running, the Worker presents the old PROXY_TOKEN to an origin that
# has already changed it, and every request 403s.
#
# The workflow only fires on a push to `main` touching deploy/, wrangler.jsonc,
# package*.json or itself -- none of which a token rotation changes. So after
# running this, trigger it by hand:
#
#   gh workflow run deploy.yml --repo wimpex18/Eesti-Keelt
#
# To ship a code change, merge to `main` and wait: Cloud Build rebuilds the
# image and redeploys Cloud Run on its own. See docs/deploy.md.
set -euo pipefail

REPO="wimpex18/Eesti-Keelt"
# Both discovered below. Set SERVICE=... only if the project holds more
# than one Cloud Run service.

fail() { echo "ERROR: $*" >&2; exit 1; }

command -v gcloud >/dev/null || fail "gcloud not found. Run this in Cloud Shell."

# Cloud Shell usually ships the GitHub CLI, but not on every image, and a
# missing tool three lines in is a bad place to stop.
if ! command -v gh >/dev/null; then
  echo "==> Installing the GitHub CLI (one-off, takes ~20s)"
  sudo apt-get -qq update && sudo apt-get -qq install -y gh \
    || fail "Could not install gh. Install it manually and re-run."
fi

# A fresh Cloud Shell has no project selected, and every gcloud command then
# fails with a message about "the [project] resource" that says nothing about
# what to do. Sort it out here instead.
echo "==> Checking which Google Cloud project is selected"
PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
if [ -z "$PROJECT" ] || [ "$PROJECT" = "(unset)" ]; then
  mapfile -t PROJECTS < <(gcloud projects list --format='value(projectId)')
  case "${#PROJECTS[@]}" in
    0) fail "This account has no Google Cloud projects." ;;
    1) PROJECT="${PROJECTS[0]}"
       echo "    None selected; you have exactly one, using it: $PROJECT"
       gcloud config set project "$PROJECT" >/dev/null 2>&1 ;;
    *) echo "    No project selected, and you have several:"
       printf '      %s\n' "${PROJECTS[@]}"
       fail "Pick one, then re-run:
    gcloud config set project THE_ONE_WITH_THE_APP
    bash deploy/setup.sh" ;;
  esac
else
  echo "    $PROJECT"
fi

# Rather than asking you which region you deployed to, ask Google. A Cloud Run
# service is findable by name across every region at once, and guessing wrong
# was the first thing that went wrong here.
echo "==> Finding the Cloud Run service"
SERVICES="$(gcloud run services list \
  --format='value(metadata.name,metadata.labels."cloud.googleapis.com/location")' \
  2>/dev/null || true)"
[ -n "$SERVICES" ] || fail "No Cloud Run services in project '$PROJECT'.
  If the app is in a different project:
    gcloud config set project THE_OTHER_ONE && bash deploy/setup.sh"

if [ -n "${SERVICE:-}" ]; then
  MATCH="$(awk -v want="$SERVICE" '$1 == want {print; exit}' <<<"$SERVICES")"
  [ -n "$MATCH" ] || fail "No service named '$SERVICE'. Found:
$(sed 's/^/    /' <<<"$SERVICES")"
elif [ "$(wc -l <<<"$SERVICES")" -eq 1 ]; then
  MATCH="$SERVICES"
else
  fail "Several Cloud Run services here:
$(sed 's/^/    /' <<<"$SERVICES")
  Say which one:
    SERVICE=the-right-name bash deploy/setup.sh"
fi

SERVICE="$(awk '{print $1}' <<<"$MATCH")"
REGION="$(awk '{print $2}' <<<"$MATCH")"
echo "    $SERVICE in $REGION"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" \
        --format='value(status.url)' 2>/dev/null || true)"
[ -n "$URL" ] || fail "Could not read the URL of '$SERVICE' in '$REGION'."
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
guarded="$(curl -s -H "x-proxy-token: $PROXY_TOKEN" "$URL/api/health" \
           | grep -o '"origin_guarded":[a-z]*' || true)"

if [ "$code_without" = "403" ] && [ "$code_with" = "200" ]; then
  echo "    OK: open request refused (403), authorised request served (200)."
elif [ "$code_without" = "200" ] && [ "$guarded" = '"origin_guarded":false' ]; then
  echo "    Not yet, and this is expected if the pull request is not merged."
  echo ""
  echo "    The environment variables are set, but the image currently running"
  echo "    was built before the guard existed, so it does not read them. The"
  echo "    guard starts working when Cloud Build rebuilds from main."
  echo ""
  echo "    After merging, wait for the build (10-15 min) and re-run:"
  echo "      bash deploy/setup.sh"
  echo "    It is safe to re-run: it rotates both tokens in both places."
elif [ "$code_without" = "200" ]; then
  echo "    WARNING: unauthorised=$code_without authorised=$code_with"
  echo "    The app is serving the open internet and reports $guarded."
  echo "    Do not enable the Worker until this reads 403."
else
  echo "    Unexpected: unauthorised=$code_without authorised=$code_with"
  echo "    Re-check with:"
  echo "      curl -o /dev/null -w '%{http_code}\n' $URL/api/health"
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
