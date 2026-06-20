#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Load env
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# Pull latest
git pull origin main

# Build & restart
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.yml up -d --remove-orphans

# Cleanup old images
docker image prune -f

echo "Deploy selesai: $(date)"
