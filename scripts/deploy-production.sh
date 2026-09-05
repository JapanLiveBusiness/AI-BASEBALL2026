#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-baseball2026}"
DATA_DIR="${DATA_DIR:-/opt/hawks-ai/data}"
SHARED_DATA_DIR="${SHARED_DATA_DIR:-}"
BRANCH="${BRANCH:-main-AI-BASEBALL}"
CONTAINER_NAME="${CONTAINER_NAME:-hawks-app}"
IMAGE_NAME="${IMAGE_NAME:-hawks-app}"
PORT="${PORT:-8501}"
DEPLOY_SHA="${DEPLOY_SHA:-}"
SKIP_GIT_FETCH="${SKIP_GIT_FETCH:-0}"
TRAEFIK_NETWORK="${TRAEFIK_NETWORK:-miki-stack_miki-net}"
TRAEFIK_HOST="${TRAEFIK_HOST:-ai-baseball-studio.f-polaris.jp}"
TRAEFIK_LEGACY_HOST="${TRAEFIK_LEGACY_HOST:-ai-baseball.f-polaris.jp}"
TRAEFIK_CONTAINER="${TRAEFIK_CONTAINER:-miki-traefik}"
AUTH_SECRETS_FILE="${AUTH_SECRETS_FILE:-/opt/hawks-ai/auth0/secrets.toml}"

cd "$APP_DIR"

if [ "$SKIP_GIT_FETCH" = "1" ]; then
  echo "[deploy] using preloaded $BRANCH revision"
else
  echo "[deploy] fetching $BRANCH"
  git fetch origin "$BRANCH"
fi
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

# Publish the versioned historical audit artifacts into the mounted production
# data directory without replacing any live schedule, prediction, BET, or
# result files maintained by the running service.
mkdir -p "$DATA_DIR"
for artifact in \
  historical_backtest_report.json \
  historical_backtest_predictions.csv; do
  install -m 0644 "$APP_DIR/data/$artifact" "$DATA_DIR/$artifact"
done

if [ -n "$DEPLOY_SHA" ]; then
  ACTUAL_SHA="$(git rev-parse HEAD)"
  if [ "$ACTUAL_SHA" != "$DEPLOY_SHA" ]; then
    echo "[deploy] expected $DEPLOY_SHA but checked out $ACTUAL_SHA"
    exit 1
  fi
fi

if ! docker network inspect "$TRAEFIK_NETWORK" >/dev/null 2>&1; then
  echo "[deploy] required Traefik network not found: $TRAEFIK_NETWORK"
  exit 1
fi

TRAEFIK_IP="$(docker inspect "$TRAEFIK_CONTAINER" --format "{{with index .NetworkSettings.Networks \"$TRAEFIK_NETWORK\"}}{{.IPAddress}}{{end}}" 2>/dev/null || true)"
if [ -z "$TRAEFIK_IP" ]; then
  echo "[deploy] Traefik container is not attached to $TRAEFIK_NETWORK: $TRAEFIK_CONTAINER"
  exit 1
fi

echo "[deploy] primary route: $TRAEFIK_HOST"
echo "[deploy] legacy route: $TRAEFIK_LEGACY_HOST"

SHORT_SHA="$(git rev-parse --short=12 HEAD)"
NEW_IMAGE="$IMAGE_NAME:$SHORT_SHA"
PREVIOUS_IMAGE="$(docker inspect -f '{{.Config.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"

echo "[deploy] building $NEW_IMAGE"
docker build -t "$NEW_IMAGE" .

# Validate configuration before stopping the currently running service.
if [ ! -f "$AUTH_SECRETS_FILE" ]; then
  echo "[deploy] Auth0 configuration required; existing container retained"
  exit 1
fi
docker run --rm --network none \
  -v "$AUTH_SECRETS_FILE:/run/auth0-secrets.toml:ro" \
  "$NEW_IMAGE" python scripts/validate_auth_config.py /run/auth0-secrets.toml

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME"
fi

start_container() {
  local image="$1"
  local shared_mount=()
  local auth_mount=()
  local auth_env=()
  if [ -n "$SHARED_DATA_DIR" ] && [ -d "$SHARED_DATA_DIR" ]; then
    shared_mount=(-v "$SHARED_DATA_DIR:/app/shared-data:ro")
  fi
  if [ -f "$AUTH_SECRETS_FILE" ]; then
    auth_mount=(-v "$AUTH_SECRETS_FILE:/app/.streamlit/secrets.toml:ro")
    auth_env=(-e "AI_BASEBALL_AUTH_ENABLED=1")
    echo "[deploy] Auth0 configuration mounted"
  else
    echo "[deploy] Auth0 configuration required"
    return 1
  fi
  docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --network "$TRAEFIK_NETWORK" \
    --dns 1.1.1.1 \
    --dns 8.8.8.8 \
    -p "127.0.0.1:$PORT:8501" \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    -v "$DATA_DIR:/app/data" \
    "${shared_mount[@]}" \
    "${auth_mount[@]}" \
    "${auth_env[@]}" \
    --label "traefik.enable=true" \
    --label "traefik.docker.network=$TRAEFIK_NETWORK" \
    --label "traefik.http.routers.ai-baseball-production.rule=Host(\`$TRAEFIK_HOST\`) || Host(\`$TRAEFIK_LEGACY_HOST\`)" \
    --label "traefik.http.routers.ai-baseball-production.entrypoints=websecure" \
    --label "traefik.http.routers.ai-baseball-production.priority=10000" \
    --label "traefik.http.routers.ai-baseball-production.tls=true" \
    --label "traefik.http.routers.ai-baseball-production.tls.certresolver=letsencrypt" \
    --label "traefik.http.routers.ai-baseball-production.service=ai-baseball-production" \
    --label "traefik.http.routers.ai-baseball-production.middlewares=ai-baseball-deploy-marker,ai-baseball-security" \
    --label "traefik.http.middlewares.ai-baseball-security.headers.contenttypenosniff=true" \
    --label "traefik.http.middlewares.ai-baseball-security.headers.framedeny=true" \
    --label "traefik.http.middlewares.ai-baseball-security.headers.referrerpolicy=no-referrer" \
    --label "traefik.http.middlewares.ai-baseball-security.headers.stsseconds=31536000" \
    --label "traefik.http.middlewares.ai-baseball-deploy-marker.headers.customresponseheaders.X-AI-Baseball-Deploy=$SHORT_SHA" \
    --label "traefik.http.services.ai-baseball-production.loadbalancer.server.port=8501" \
    "$image"
}

rollback() {
  echo "[deploy] health check failed"
  docker logs --tail 100 "$CONTAINER_NAME" || true
  docker rm -f "$CONTAINER_NAME" || true
  if [ -n "$PREVIOUS_IMAGE" ] && docker image inspect "$PREVIOUS_IMAGE" >/dev/null 2>&1; then
    echo "[deploy] rolling back to $PREVIOUS_IMAGE"
    start_container "$PREVIOUS_IMAGE"
  fi
  exit 1
}

start_container "$NEW_IMAGE"

for attempt in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/_stcore/health" >/dev/null; then
    echo "[deploy] app healthy: $NEW_IMAGE"
    if curl -k -fsSI \
      --resolve "$TRAEFIK_HOST:443:$TRAEFIK_IP" \
      "https://$TRAEFIK_HOST/_stcore/health" | grep -Fqi "x-ai-baseball-deploy: $SHORT_SHA"; then
      echo "[deploy] primary Traefik route healthy: https://$TRAEFIK_HOST/ -> $CONTAINER_NAME:8501"
    else
      echo "[deploy] primary Traefik route health check failed for https://$TRAEFIK_HOST/"
      rollback
    fi
    if curl -k -fsSI \
      --resolve "$TRAEFIK_LEGACY_HOST:443:$TRAEFIK_IP" \
      "https://$TRAEFIK_LEGACY_HOST/_stcore/health" | grep -Fqi "x-ai-baseball-deploy: $SHORT_SHA"; then
      echo "[deploy] legacy Traefik route healthy: https://$TRAEFIK_LEGACY_HOST/ -> $CONTAINER_NAME:8501"
      docker tag "$NEW_IMAGE" "$IMAGE_NAME:latest"
      exit 0
    fi
    echo "[deploy] legacy Traefik route health check failed for https://$TRAEFIK_LEGACY_HOST/"
    rollback
  fi
  sleep 2
done

rollback
