#!/usr/bin/env bash
set -e

echo "Starting FastAPI backend on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &

sleep 2

echo "Starting Streamlit on Render's port: $PORT..."
streamlit run merged_dashboards.py --server.port $PORT --server.address 0.0.0.0