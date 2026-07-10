#!/usr/bin/env bash
# Start Prelegal locally on Linux using Docker Compose.
# Usage: scripts/start-linux.sh [--rebuild]

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH. Install Docker Engine first." >&2
  exit 1
fi

REBUILD=""
if [ "${1:-}" = "--rebuild" ] || [ "${1:-}" = "-r" ]; then
  REBUILD="--build"
fi

# On Linux, `docker compose` is provided by the docker-compose-plugin or the
# standalone `docker-compose` binary. The plugin is preferred and is what Docker
# Engine installs by default on modern distros.
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "ERROR: neither 'docker compose' (v2 plugin) nor 'docker-compose' (v1) is available." >&2
  exit 1
fi

echo "Starting Prelegal ($COMPOSE_CMD up -d $REBUILD)..."
$COMPOSE_CMD up -d $REBUILD

echo "Waiting for /healthz..."
for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/dev/null 2>&1; then
    echo "Prelegal is up at http://localhost:8000"
    exit 0
  fi
  sleep 1
done

echo "ERROR: Prelegal did not become healthy in 30s. Recent logs:" >&2
$COMPOSE_CMD logs --tail=80 app >&2
exit 1