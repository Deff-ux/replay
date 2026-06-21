#!/bin/bash
# Replay — Seed config from environments.yaml
# Usage: ./seed-config.sh [--env-only] [--users-only] [--reset] [--dry-run]

CONTAINER="docker-replay-1"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "❌ Container '${CONTAINER}' not running. Start it first."
    exit 1
fi

exec docker exec -it "${CONTAINER}" python3 /app/backend/scripts/seed_config.py "$@"
