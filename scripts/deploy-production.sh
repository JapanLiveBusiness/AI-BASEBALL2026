#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-baseball2026}"
DATA_DIR="${DATA_DIR:-/opt/hawks-ai/data}"
BRANCH="${BRANCH:-main-AI-BASEBALL}"
CONTAINER_NAME="${CONTAINER_NAME:-hawks-app}"
IMAGE_NAME="${IMAGE_NAME:-hawks-app}"
PORT="${PORT:-8501}"
DEPLOY_SHA="${DEPLOY_SHA:-}"
TRAEFIK_NETWORK="${TRAEFIK_NETWORK:-miki-stack_miki-net}"
TRAEFIK_HOST="${TRAEFIK_HOST:-ai-baseball-studio.f-polaris.jp}"
TRAEFIK_LEGACY_HOST="${TRAEFIK_LEGACY_HOST-ai-baseball.f-polaris.jp}"
TRAEFIK_CONTAINER="${TRAEFIK_CONTAINER:-miki-traefik}"
TRAEFIK_ROUTER_NAME="${TRAEFIK_ROUTER_NAME:-ai-baseball}"
TRAEFIK_SERVICE_NAME="${TRAEFIK_SERVICE_NAME:-ai-baseball}"
TRAEFIK_PRIORITY="${TRAEFIK_PRIORITY:-}"
STREAMLIT_SECRETS_FILE="${STREAMLIT_SECRETS_FILE:-}"
AUTH_ALLOWED_EMAILS="${AUTH_ALLOWED_EMAILS:-tsutsumi@japanlivebusiness.com}"

cd "$APP_DIR"

echo "[deploy] fetching $BRANCH"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

mkdir -p "$DATA_DIR"

for artifact in \
  historical_games_2017_2026.json \
  historical_backtest_report.json \
  historical_backtest_predictions.csv; do
  if [ -f "$APP_DIR/data/$artifact" ]; then
    install -m 0644 "$APP_DIR/data/$artifact" "$DATA_DIR/$artifact"
  fi
done

for artifact in \
  npb_today.json \
  today_ai_predictions.json \
  pregame_predictions.json \
  bet_records.json; do
  if [ ! -s "$DATA_DIR/$artifact" ] && [ -s "$APP_DIR/data/$artifact" ]; then
    install -m 0644 "$APP_DIR/data/$artifact" "$DATA_DIR/$artifact"
    echo "[deploy] seeded fallback dashboard data: $artifact"
  fi
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

if [ -n "$STREAMLIT_SECRETS_FILE" ] && [ ! -s "$STREAMLIT_SECRETS_FILE" ]; then
  echo "[deploy] Streamlit secrets file is missing or empty: $STREAMLIT_SECRETS_FILE"
  exit 1
fi

echo "[deploy] primary route: $TRAEFIK_HOST"
if [ -n "$TRAEFIK_LEGACY_HOST" ]; then
  echo "[deploy] legacy route: $TRAEFIK_LEGACY_HOST"
fi

SHORT_SHA="$(git rev-parse --short=12 HEAD)"
NEW_IMAGE="$IMAGE_NAME:$SHORT_SHA"
PREVIOUS_IMAGE="$(docker inspect -f '{{.Config.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"

echo "[deploy] building $NEW_IMAGE"
docker build -t "$NEW_IMAGE" .

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME"
fi

start_container() {
  local image="$1"
  local router_rule
  local -a labels
  local -a auth_args

  router_rule="Host(\`$TRAEFIK_HOST\`)"
  if [ -n "$TRAEFIK_LEGACY_HOST" ]; then
    router_rule="$router_rule || Host(\`$TRAEFIK_LEGACY_HOST\`)"
  fi

  labels=(
    --label "traefik.enable=true"
    --label "traefik.docker.network=$TRAEFIK_NETWORK"
    --label "traefik.http.routers.$TRAEFIK_ROUTER_NAME.rule=$router_rule"
    --label "traefik.http.routers.$TRAEFIK_ROUTER_NAME.entrypoints=websecure"
    --label "traefik.http.routers.$TRAEFIK_ROUTER_NAME.tls=true"
    --label "traefik.http.routers.$TRAEFIK_ROUTER_NAME.tls.certresolver=letsencrypt"
    --label "traefik.http.routers.$TRAEFIK_ROUTER_NAME.service=$TRAEFIK_SERVICE_NAME"
    --label "traefik.http.services.$TRAEFIK_SERVICE_NAME.loadbalancer.server.port=8501"
  )

  if [ -n "$TRAEFIK_PRIORITY" ]; then
    labels+=(--label "traefik.http.routers.$TRAEFIK_ROUTER_NAME.priority=$TRAEFIK_PRIORITY")
  fi

  auth_args=(--env "AUTH_ALLOWED_EMAILS=$AUTH_ALLOWED_EMAILS")
  if [ -n "$STREAMLIT_SECRETS_FILE" ]; then
    auth_args+=(--volume "$STREAMLIT_SECRETS_FILE:/app/.streamlit/secrets.toml:ro")
  fi

  docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --network "$TRAEFIK_NETWORK" \
    -p "$PORT:8501" \
    -v "$DATA_DIR:/app/data" \
    "${auth_args[@]}" \
    "${labels[@]}" \
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
    if curl -k -fsS \
      --resolve "$TRAEFIK_HOST:443:$TRAEFIK_IP" \
      "https://$TRAEFIK_HOST/_stcore/health" >/dev/null; then
      echo "[deploy] primary Traefik route healthy: https://$TRAEFIK_HOST/ -> $CONTAINER_NAME:8501"
    else
      echo "[deploy] primary Traefik route health check failed for https://$TRAEFIK_HOST/"
      rollback
    fi

    if [ -n "$TRAEFIK_LEGACY_HOST" ]; then
      if curl -k -fsS \
        --resolve "$TRAEFIK_LEGACY_HOST:443:$TRAEFIK_IP" \
        "https://$TRAEFIK_LEGACY_HOST/_stcore/health" >/dev/null; then
        echo "[deploy] legacy Traefik route healthy: https://$TRAEFIK_LEGACY_HOST/ -> $CONTAINER_NAME:8501"
      else
        echo "[deploy] legacy Traefik route health check failed for https://$TRAEFIK_LEGACY_HOST/"
        rollback
      fi
    fi

    docker tag "$NEW_IMAGE" "$IMAGE_NAME:latest"
    exit 0
  fi
  sleep 2
done

rollback
