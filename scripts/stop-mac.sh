#!/usr/bin/env bash
# Stop Prelegal locally on macOS. Containers are removed; the image is kept
# so a subsequent `start-mac.sh` does not need to rebuild.

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH." >&2
  exit 1
fi

echo "Stopping Prelegal (compose down)..."
docker compose down

echo "Prelegal stopped."