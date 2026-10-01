#!/usr/bin/env bash
# Fail before pushing secrets when CI cannot read a configured VPC service.
set -euo pipefail
services="$(node --input-type=module - "${1:-wrangler.jsonc}" <<'JS'
import { experimental_readRawConfig } from "wrangler";
const { rawConfig } = experimental_readRawConfig({ config: process.argv[2] });
for (const service of rawConfig.vpc_services ?? []) {
  console.log(service.service_id);
}
JS
)"
while IFS= read -r service; do
  [ -n "$service" ] || continue
  if ! npx wrangler vpc service get "$service" >/dev/null; then
    echo "::error::Deployment credential cannot access configured VPC service $service."
    echo "Grant Connectivity Directory Bind in the configured Cloudflare account; see deploy/home-asr/README.md."
    exit 1
  fi
done <<<"$services"
