#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/user/apps/AI-BASEBALL2026}"
DATA_DIR="${DATA_DIR:-/opt/hawks-ai/data}"
SHARED_DATA_DIR="${SHARED_DATA_DIR:-/opt/hawks-ai/research-data}"
BRANCH="${BRANCH:-main-AI-BASEBALL}"
CONTAINER_NAME="${CONTAINER_NAME:-hawks-app}"
IMAGE_NAME="${IMAGE_NAME:-hawks-app}"
PORT="${PORT:-8501}"
DEPLOY_SHA="${DEPLOY_SHA:-}"
SKIP_GIT_FETCH="${SKIP_GIT_FETCH:-0}"
AUTH_SECRETS_FILE="${AUTH_SECRETS_FILE:-/opt/hawks-ai/auth0/secrets.toml}"

cd "$APP_DIR"
mkdir -p "$DATA_DIR"

if [ "$SKIP_GIT_FETCH" = "1" ]; then
  echo "[deploy-info] using preloaded $BRANCH revision"
else
  git fetch origin "$BRANCH"
fi

git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

if [ -n "$DEPLOY_SHA" ]; then
  ACTUAL_SHA="$(git rev-parse HEAD)"
  if [ "$ACTUAL_SHA" != "$DEPLOY_SHA" ]; then
    echo "[deploy-info] expected $DEPLOY_SHA but checked out $ACTUAL_SHA"
    exit 1
  fi
fi

if [ -x /usr/local/bin/hawks-data-sync ]; then
  echo "[deploy-info] refreshing baseball data"
  /usr/local/bin/hawks-data-sync || echo "[deploy-info] live refresh unavailable; using latest cached data"
fi

if [ ! -f "$AUTH_SECRETS_FILE" ]; then
  echo "[deploy-info] Auth0 configuration missing; existing container retained"
  exit 1
fi

SHORT_SHA="$(git rev-parse --short=12 HEAD)"
NEW_IMAGE="$IMAGE_NAME:$SHORT_SHA"
PREVIOUS_IMAGE="$(docker inspect -f '{{.Config.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"

echo "[deploy-info] building $NEW_IMAGE"
docker build -t "$NEW_IMAGE" .

docker run --rm --network none \
  --security-opt no-new-privileges:true \
  --cap-drop ALL --cap-add DAC_OVERRIDE \
  -v "$AUTH_SECRETS_FILE:/run/auth0-secrets.toml:ro" \
  "$NEW_IMAGE" python scripts/validate_auth_config.py /run/auth0-secrets.toml

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME"
fi

start_container() {
  local image="$1"
  local shared_mount=()
  if [ -d "$SHARED_DATA_DIR" ]; then
    shared_mount=(-v "$SHARED_DATA_DIR:/app/shared-data:ro")
  fi

  docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --network bridge \
    --dns 1.1.1.1 \
    --dns 8.8.8.8 \
    -p "127.0.0.1:$PORT:8501" \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    --cap-add DAC_OVERRIDE \
    -v "$DATA_DIR:/app/data" \
    -v "$AUTH_SECRETS_FILE:/app/.streamlit/secrets.toml:ro" \
    -e "AI_BASEBALL_AUTH_ENABLED=1" \
    -e "AI_BASEBALL_ENTRYPOINT=info_main.py" \
    -e "AI_BASEBALL_SHARED_DATA_DIR=/app/shared-data" \
    "${shared_mount[@]}" \
    "$image"
}

rollback() {
  echo "[deploy-info] health check failed"
  docker logs --tail 120 "$CONTAINER_NAME" || true
  docker rm -f "$CONTAINER_NAME" || true
  if [ -n "$PREVIOUS_IMAGE" ] && docker image inspect "$PREVIOUS_IMAGE" >/dev/null 2>&1; then
    echo "[deploy-info] rolling back to $PREVIOUS_IMAGE"
    start_container "$PREVIOUS_IMAGE"
  fi
  exit 1
}

start_container "$NEW_IMAGE"

for attempt in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/_stcore/health" >/dev/null; then
    echo "[deploy-info] app healthy: $NEW_IMAGE"
    if ! docker exec "$CONTAINER_NAME" python /app/scripts/validate_runtime_data.py \
      --data-dir /app/data \
      --shared-data-dir /app/shared-data; then
      echo "[deploy-info] runtime data validation failed"
      rollback
    fi
    docker tag "$NEW_IMAGE" "$IMAGE_NAME:latest"
    echo "[deploy-info] information-only production container is running"
    exit 0
  fi
  sleep 2
done

rollback
