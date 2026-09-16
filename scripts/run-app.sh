#!/usr/bin/env sh
set -eu

APP_ENTRYPOINT="${AI_BASEBALL_ENTRYPOINT:-main.py}"

refresh_schedule() {
  while true; do
    python /app/scripts/refresh_npb_schedule_cache.py || true
    python /app/scripts/refresh_npb_results_cache.py || true
    sleep "${NPB_SCHEDULE_INTERVAL:-21600}"
  done
}

if [ "$APP_ENTRYPOINT" = "info_main.py" ]; then
  echo "[run-app] starting information-only baseball dashboard"
  refresh_schedule &
  exec streamlit run /app/info_main.py --server.port=8501 --server.address=0.0.0.0
fi

refresh_metrics() {
  while true; do
    python /app/prediction_metrics.py || true
    sleep "${PREDICTION_METRICS_INTERVAL:-30}"
  done
}

refresh_prediction_results() {
  while true; do
    python /app/prediction_results.py || true
    sleep "${PREDICTION_RESULTS_INTERVAL:-60}"
  done
}

python /app/prediction_metrics.py || true
python /app/prediction_results.py || true
refresh_metrics &
refresh_prediction_results &
refresh_schedule &
exec streamlit run /app/main.py --server.port=8501 --server.address=0.0.0.0
