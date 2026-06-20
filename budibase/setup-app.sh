#!/bin/sh
set -eu

BUDIBASE_URL="${BUDIBASE_URL:-http://budibase:80}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

printf 'Waiting for Budibase at %s\n' "$BUDIBASE_URL"
for i in $(seq 1 60); do
  if curl -fsS "$BUDIBASE_URL/api/global/status" >/dev/null 2>&1 || curl -fsS "$BUDIBASE_URL" >/dev/null 2>&1; then
    printf 'Budibase is ready after %ss\n' "$i"
    exec node "$SCRIPT_DIR/setup-app.js"
  fi
  sleep 1
done

echo "Budibase did not become ready within 60 seconds" >&2
exit 1
