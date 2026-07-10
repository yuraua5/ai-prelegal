#!/usr/bin/env bash
# Start Prelegal locally on macOS using Docker Compose.
# Usage: scripts/start-mac.sh [--rebuild]

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH. Install Docker Desktop for Mac first." >&2
  exit 1
fi

REBUILD=""
if [ "${1:-}" = "--rebuild" ] || [ "${1:-}" = "-r" ]; then
  REBUILD="--build"
fi

echo "Starting Prelegal (compose up -d $REBUILD)..."
docker compose up -d $REBUILD

echo "Waiting for /healthz..."
for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/dev/null 2>&1; then
    echo "Prelegal is up at http://localhost:8000"
    exit 0
  fi
  sleep 1
done

echo "ERROR: Prelegal did not become healthy in 30s. Recent logs:" >&2
docker compose logs --tail=80 app >&2
exit 1