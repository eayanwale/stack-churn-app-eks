#!/usr/bin/env bash
# Local dev run (no Docker). Trains the model if it is missing.
set -e
[ -f model/churn_model.joblib ] || python3 train/train_model.py
export INFERENCE_MODE=${INFERENCE_MODE:-local}
export PORT=${PORT:-8080}
exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 60 wsgi:app
