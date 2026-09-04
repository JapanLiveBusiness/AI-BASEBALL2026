#!/usr/bin/env sh
set -eu

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
exec streamlit run main.py --server.port=8501 --server.address=0.0.0.0
