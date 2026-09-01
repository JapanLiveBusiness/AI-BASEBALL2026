#!/usr/bin/env bash
set -euo pipefail

SITE_URL="${SITE_URL:-https://ai-baseball.f-polaris.jp/}"
CF_ACCESS_CLIENT_ID="${CF_ACCESS_CLIENT_ID:-}"
CF_ACCESS_CLIENT_SECRET="${CF_ACCESS_CLIENT_SECRET:-}"

if [ -z "$CF_ACCESS_CLIENT_ID" ] || [ -z "$CF_ACCESS_CLIENT_SECRET" ]; then
  echo "Cloudflare Access service token is not configured; verifying that anonymous access is blocked by Access"
  headers="$(mktemp)"
  trap 'rm -f "$headers"' EXIT

  status="$(curl \
    --silent \
    --show-error \
    --output /dev/null \
    --dump-header "$headers" \
    --max-time 15 \
    --write-out '%{http_code}' \
    "$SITE_URL")"

  location="$(awk 'BEGIN{IGNORECASE=1} /^location:/ {sub(/^[^:]+:[[:space:]]*/, ""); gsub(/\r/, ""); print; exit}' "$headers")"
  echo "Anonymous HTTP status: $status"

  if [[ "$status" =~ ^30[12378]$ ]] && [[ "$location" == *"cloudflareaccess.com"* || "$location" == *"/cdn-cgi/access/"* ]]; then
    echo "Cloudflare Access is enforcing authentication for anonymous requests"
    exit 0
  fi

  if [ "$status" = "200" ]; then
    echo "::error::Anonymous request reached the production site with HTTP 200; Cloudflare Access is not enforcing authentication"
  else
    echo "::error::Anonymous request was not recognized as a Cloudflare Access login redirect (status=$status)"
  fi
  exit 1
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
