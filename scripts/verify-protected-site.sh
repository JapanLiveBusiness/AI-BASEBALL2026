#!/usr/bin/env bash
set -euo pipefail

SITE_URL="${SITE_URL:-https://ai-baseball.f-polaris.jp/}"
CF_ACCESS_CLIENT_ID="${CF_ACCESS_CLIENT_ID:-}"
CF_ACCESS_CLIENT_SECRET="${CF_ACCESS_CLIENT_SECRET:-}"

if [ -z "$CF_ACCESS_CLIENT_ID" ] || [ -z "$CF_ACCESS_CLIENT_SECRET" ]; then
  echo "::warning::Cloudflare Access service token is not configured; protected public-site verification skipped"
  echo "Configure CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET as GitHub Actions secrets before enforcing Cloudflare Access."
  exit 0
fi

for attempt in $(seq 1 20); do
  if curl \
    --fail \
    --silent \
    --show-error \
    --location \
    --max-time 10 \
    --header "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" \
    --header "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET" \
    "$SITE_URL" >/dev/null; then
    echo "Protected production site is responding through Cloudflare Access"
    exit 0
  fi
  sleep 3
done

echo "Protected production site health check failed"
exit 1
