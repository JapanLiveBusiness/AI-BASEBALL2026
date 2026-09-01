#!/usr/bin/env sh
set -eu

refresh_metrics() {
  while true; do
    python /app/prediction_metrics.py || true
    sleep "${PREDICTION_METRICS_INTERVAL:-30}"
  done
}

python /app/prediction_metrics.py || true
refresh_metrics &
exec streamlit run main.py --server.port=8501 --server.address=0.0.0.0
