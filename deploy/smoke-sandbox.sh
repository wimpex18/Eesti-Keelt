#!/usr/bin/env bash
# Source from smoke with URL and its auth array. Only confirmed guest traffic
# may submit the fixed writing sample; failed probes remain read-only.
smoke_sandbox() {
  local name identity profile
  name="smoke-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
  if ! identity="$(curl -sf "${auth[@]}" -H "x-eesti-guest: $name" "$URL/api/auth/me")"; then
    echo "::error::Worker account endpoint unavailable; deploy the current Worker."
    return 1
  fi
  if ! jq -e '.scope == "guest"' <<<"$identity" >/dev/null; then
    echo "::error::Worker did not isolate the smoke sandbox; deep submissions refused."
    return 1
  fi
  if ! profile="$(curl -sf "${auth[@]}" -H "x-eesti-guest: $name" "$URL/api/me")"; then
    echo "::error::Origin sandbox profile unavailable; deep submissions refused."
    return 1
  fi
  if ! jq -e '.scope == "guest"' <<<"$profile" >/dev/null; then
    echo "::error::Origin did not confirm guest scope; deep submissions refused."
    return 1
  fi
  auth+=(-H "x-eesti-guest: $name")
  echo "smoke sandbox ........... OK (Worker and origin confirm guest)"
}
smoke_sandbox
