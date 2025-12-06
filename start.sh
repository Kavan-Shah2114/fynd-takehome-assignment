#!/usr/bin/env bash
set -e

# start.sh - Start uvicorn on $PORT (Render expects your web service to bind $PORT)
# Use $PORT provided by Render.

PORT="${PORT:-$1:-8000}"  # allow override but default to 8000 locally if needed

echo "Starting FastAPI backend with uvicorn on 0.0.0.0:${PORT} ..."
uvicorn main:app --host 0.0.0.0 --port "${PORT}"